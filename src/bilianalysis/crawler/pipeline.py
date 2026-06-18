"""爬取编排：速率控制、重试、续爬、并发模式。"""
import asyncio
import datetime
import random
import time
from typing import Literal

from pydantic import BaseModel
import aiohttp

from bilianalysis.config import CrawlerSection, load_config
from .api import list_series, get_weekly_videos
from .storage import save_week, load_progress, save_progress, get_pending_weeks
from bilianalysis.utils.fetch import create_session, HttpError
from .signer import fetch_mixin_key, WbiSigner

def _jitter(base: float) -> float:
    """在基础延迟上叠加 ±1 秒随机抖动，避免请求间隔过于规律被反爬。"""
    return base + random.uniform(-1, 1)


class CrawlReport(BaseModel):
    total: int
    crawled: int
    skipped: int
    failed: int
    failed_weeks: dict[int, str]
    duration_seconds: float


async def run(config: CrawlerSection | None = None) -> CrawlReport:
    """执行一次完整爬取。供外部模块调用。"""
    if config is None:
        config = load_config().crawler
    start_time = time.monotonic()
    crawled_count = 0
    failed_count = 0
    failed_details: dict[int, str] = {}

    session = create_session()
    mixin_key = await fetch_mixin_key(session)
    signer = WbiSigner(mixin_key)
    refresher = lambda s: fetch_mixin_key(s)
    try:
        # 1. 获取所有期号
        series = await list_series(session, signer)
        if not series:
            return CrawlReport(
                total=0, crawled=0, skipped=0, failed=0,
                failed_weeks={}, duration_seconds=time.monotonic() - start_time
            )
        latest = max(s["number"] for s in series)
        total = latest

        # 2. 获取待爬列表
        retry_list, pending_list = await get_pending_weeks(latest)

        # 计算已跳过数（之前已成功爬取的）
        progress = await load_progress()
        already_crawled = set(progress.crawled)
        failed_set = set(int(k) for k in progress.failed.keys())
        already_done = already_crawled - failed_set
        skipped_count = len(already_done)

        # 3. 先处理历史失败期号（用 _crawl_one 复用空响应检测 + 密钥刷新）
        for number in retry_list:
            success, err_msg = await _crawl_one(session, number, config,
                                                 signer, refresher, max_retries=1)
            if success:
                crawled_count += 1
            else:
                failed_count += 1
                failed_details[number] = err_msg

        # 4. 处理新期号
        if config.mode == "sequential":
            for number in pending_list:
                success, err_msg = await _crawl_one(session, number, config,
                                                     signer, refresher)
                if success:
                    crawled_count += 1
                else:
                    failed_count += 1
                    failed_details[number] = err_msg
                await asyncio.sleep(_jitter(config.request_delay))
        else:
            semaphore = asyncio.Semaphore(config.concurrency)

            async def crawl_with_semaphore(number: int):
                async with semaphore:
                    success, err_msg = await _crawl_one(session, number, config,
                                                         signer, refresher)
                    return number, success, err_msg

            results = await asyncio.gather(
                *(crawl_with_semaphore(n) for n in pending_list)
            )
            for number, success, err_msg in results:
                if success:
                    crawled_count += 1
                else:
                    failed_count += 1
                    failed_details[number] = err_msg

        # 5. 更新最后运行时间
        progress = await load_progress()
        progress.last_run = datetime.datetime.now()
        await save_progress(progress)

        duration = time.monotonic() - start_time
        return CrawlReport(
            total=total,
            crawled=crawled_count,
            skipped=skipped_count,
            failed=failed_count,
            failed_weeks=failed_details,
            duration_seconds=round(duration, 2)
        )
    finally:
        await session.close()


async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection, signer: WbiSigner,
                     mixin_refresher,
                     max_retries: int | None = None) -> tuple[bool, str]:
    """爬取单期，含重试逻辑和 WBI 密钥自动刷新。返回 (成功, 错误信息)。"""
    retries = max_retries if max_retries is not None else config.max_retries
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            data = await get_weekly_videos(session, number, signer)
        except HttpError as e:
            last_error = str(e)
            # 空响应或鉴权失败 → 刷新 WBI 密钥
            if ("empty" in last_error or "-403" in last_error or
                "-401" in last_error or "-352" in last_error):
                new_key = await mixin_refresher(session)
                signer._key = new_key
            if attempt < retries:
                await asyncio.sleep(_jitter(config.retry_delay))
            continue

        # 成功前检测空响应
        if not data.get("list") and not data.get("config"):
            last_error = "HTTP 200: empty response"
            new_key = await mixin_refresher(session)
            signer._key = new_key
            if attempt < retries:
                await asyncio.sleep(_jitter(config.retry_delay))
            continue

        # 成功
        await save_week(number, {"number": number, "config": data.get("config", {}),
                                 "videos": data.get("list", [])})
        progress = await load_progress()
        if number not in progress.crawled:
            progress.crawled.append(number)
        progress.failed.pop(number, None)
        await save_progress(progress)
        return True, ""

    # 全部重试失败
    progress = await load_progress()
    progress.failed[number] = last_error
    await save_progress(progress)
    return False, last_error
