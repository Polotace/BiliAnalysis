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
from bilianalysis.utils.fetch import (
    create_session, rotate_session_headers, HttpError, BiliCodeError,
)
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

    cookie = config.cookie or ""
    session = create_session(cookie=cookie)
    mixin_key = await fetch_mixin_key(session, cookie=cookie)
    signer = WbiSigner(mixin_key)
    refresher = lambda s: fetch_mixin_key(s, cookie=cookie)
    request_count = 0  # 跟踪已发送请求数，用于主动密钥刷新和 session 轮换
    retry_delay_acc = config.retry_delay  # 指数退避的动态延迟
    try:
        # 1. 获取所有期号
        series = await list_series(session, signer)
        request_count += 1
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

        # 2.5. 包装器：处理请求计数 + 主动刷新 + Session 轮换
        async def _crawl_with_rotation(number: int, max_retries: int | None = None) -> tuple[bool, str]:
            nonlocal session, signer, request_count, retry_delay_acc

            # 主动刷新 WBI 密钥（到达间隔阈值）
            if config.key_refresh_interval > 0 and request_count > 0 \
                    and request_count % config.key_refresh_interval == 0:
                signer._key = await refresher(session)

            # Session 轮换（模拟新连接，避开长连接指纹）
            if config.max_requests_per_session > 0 and request_count > 0 \
                    and request_count % config.max_requests_per_session == 0:
                await session.close()
                session = create_session(cookie=config.cookie)
                rotate_session_headers(session, cookie=config.cookie)

            success, err_msg, reqs = await _crawl_one(
                session, number, config, signer, refresher,
                retry_delay_acc, max_retries=max_retries,
            )
            request_count += reqs
            if success:
                retry_delay_acc = config.retry_delay  # 重置退避
            else:
                retry_delay_acc = min(retry_delay_acc * 1.3, 30.0)  # 累积退避
            return success, err_msg

        # 3. 先处理历史失败期号
        for number in retry_list:
            success, err_msg = await _crawl_with_rotation(number, max_retries=1)
            if success:
                crawled_count += 1
            else:
                failed_count += 1
                failed_details[number] = err_msg

        # 4. 处理新期号
        if config.mode == "sequential":
            for number in pending_list:
                success, err_msg = await _crawl_with_rotation(number)
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
                    success, err_msg = await _crawl_with_rotation(number)
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
        if not session.closed:
            await session.close()


async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection, signer: WbiSigner,
                     mixin_refresher, retry_delay: float,
                     max_retries: int | None = None) -> tuple[bool, str, int]:
    """爬取单期，含重试 + WBI 刷新 + 指数退避 + 限流处理。
    返回 (成功, 错误信息, 本次尝试的请求数)。"""
    retries = max_retries if max_retries is not None else config.max_retries
    last_error = ""
    delay = retry_delay  # 指数退避起点
    reqs_this_week = 0

    for attempt in range(1, retries + 1):
        try:
            data = await get_weekly_videos(session, number, signer)
            reqs_this_week += 1
        except BiliCodeError as e:
            last_error = str(e)
            reqs_this_week += 1
            # -352: WBI key expired, -403: forbidden, -401: unauthorized
            if e.bili_code in (-352, -403, -401):
                new_key = await mixin_refresher(session)
                signer._key = new_key
            # -412: rate limited — exponential backoff
            elif e.bili_code == -412:
                delay = min(delay * 2, 60.0)  # cap at 60s
            if attempt < retries:
                await asyncio.sleep(_jitter(delay))
            continue
        except HttpError as e:
            last_error = str(e)
            reqs_this_week += 1
            # HTTP 412: rate limited
            if "412" in last_error:
                delay = min(delay * 2, 60.0)
            # Auth-related HTTP errors → refresh WBI key
            elif "403" in last_error or "401" in last_error:
                new_key = await mixin_refresher(session)
                signer._key = new_key
            if attempt < retries:
                await asyncio.sleep(_jitter(delay))
            continue

        # 成功前检测空响应
        if not data.get("list") and not data.get("config"):
            last_error = "HTTP 200: empty response"
            new_key = await mixin_refresher(session)
            signer._key = new_key
            delay = min(delay * 1.5, 30.0)  # 温和退避
            if attempt < retries:
                await asyncio.sleep(_jitter(delay))
            continue

        # 成功 → 重置退避延迟
        await save_week(number, {"number": number, "config": data.get("config", {}),
                                 "videos": data.get("list", [])})
        progress = await load_progress()
        if number not in progress.crawled:
            progress.crawled.append(number)
        progress.failed.pop(number, None)
        await save_progress(progress)
        return True, "", reqs_this_week

    # 全部重试失败
    progress = await load_progress()
    progress.failed[number] = last_error
    await save_progress(progress)
    return False, last_error, reqs_this_week
