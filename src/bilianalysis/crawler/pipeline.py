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
    old_sessions: list[aiohttp.ClientSession] = []  # 旋转时替换的旧 session，finally 关闭

    # ── 全局共享限流状态（所有并发请求统一退避）──
    rate_limit = {
        "delay": config.retry_delay,  # 所有 worker 共用
        "lock": asyncio.Lock(),
        "cool_until": 0.0,
        "hits_since_rotate": 0,       # 本次 session 累计 -352 次数
    }

    async def _maybe_rotate_on_rate_limit():
        """连续 -352 超阈值 → 换 session（新设备指纹），重置 IP 维度的限流压力。"""
        nonlocal session, signer
        rotate_threshold = 3
        async with rate_limit["lock"]:
            rate_limit["hits_since_rotate"] += 1
            should_rotate = rate_limit["hits_since_rotate"] >= rotate_threshold
        if should_rotate:
            print(f"  🔄 Session rotation (hit {rotate_threshold}+ rate limits, "
                  f"new device ID → may reset IP-level counter)")
            # 创建新 session，旧 session 记入待清理列表
            async with rate_limit["lock"]:
                old_sessions.append(session)
                session = create_session(cookie=config.cookie)
                signer._key = await refresher(session)
                rate_limit["hits_since_rotate"] = 0
                # 只降到 base 的 2 倍（IP 瓶颈没解决，不归零）
                rate_limit["delay"] = max(config.retry_delay * 2, rate_limit["delay"] * 0.3)

    async def _on_rate_hit(msg: str, multiplier: float = 2.0, cap: float = 60.0):
        """全局限流命中：所有 worker 统一退避 + 连续命中换 session。"""
        async with rate_limit["lock"]:
            rate_limit["delay"] = min(rate_limit["delay"] * multiplier, cap)
            rate_limit["cool_until"] = time.monotonic() + rate_limit["delay"]
            print(f"  ⏳ {msg}, global delay now {rate_limit['delay']:.1f}s")

    async def _on_success():
        """成功后逐步恢复延迟。"""
        async with rate_limit["lock"]:
            rate_limit["delay"] = max(config.retry_delay, rate_limit["delay"] * 0.85)

    async def _wait_if_cooling():
        """如果需要冷却，等待冷却结束。"""
        while True:
            async with rate_limit["lock"]:
                remaining = rate_limit["cool_until"] - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.sleep(max(remaining, 0.5))
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

        # 2.5. 包装器：处理请求计数 + 全局限流 + 主动刷新 + Session 轮换
        async def _crawl_with_rotation(number: int, max_retries: int | None = None) -> tuple[bool, str]:
            nonlocal session, signer, request_count

            # 全局冷却等待
            await _wait_if_cooling()

            # 主动刷新 WBI 密钥（到达间隔阈值）
            if config.key_refresh_interval > 0 and request_count > 0 \
                    and request_count % config.key_refresh_interval == 0:
                print(f"  🔑 Proactive WBI key refresh (request #{request_count})")
                signer._key = await refresher(session)

            # Session 轮换（模拟新连接，避开长连接指纹）
            if config.max_requests_per_session > 0 and request_count > 0 \
                    and request_count % config.max_requests_per_session == 0:
                print(f"  🔄 Session rotation (request #{request_count}, new device fingerprint)")
                await session.close()
                session = create_session(cookie=config.cookie)

            async with rate_limit["lock"]:
                current_delay = rate_limit["delay"]
            success, err_msg, reqs = await _crawl_one(
                session, number, config, signer, refresher,
                current_delay, max_retries=max_retries,
                on_rate_hit=_on_rate_hit, on_success=_on_success,
                on_rate_rotate=_maybe_rotate_on_rate_limit,
            )
            request_count += reqs
            if success:
                await _on_success()
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
        for s in old_sessions:
            if not s.closed:
                await s.close()
        if not session.closed:
            await session.close()


async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection, signer: WbiSigner,
                     mixin_refresher, retry_delay: float,
                     max_retries: int | None = None,
                     on_rate_hit=None, on_success=None,
                     on_rate_rotate=None) -> tuple[bool, str, int]:
    """爬取单期，含重试 + WBI 刷新 + 全局限流退避。
    返回 (成功, 错误信息, 本次尝试的请求数)。"""
    retries = max_retries if max_retries is not None else config.max_retries
    last_error = ""
    reqs_this_week = 0

    for attempt in range(1, retries + 1):
        try:
            data = await get_weekly_videos(session, number, signer)
            reqs_this_week += 1
        except BiliCodeError as e:
            last_error = str(e)
            reqs_this_week += 1
            # -352: rate limited → 全局限流退避 + 连续命中换 session
            if e.bili_code == -352:
                if on_rate_hit:
                    await on_rate_hit(f"Week #{number} rate limited (code=-352)",
                                     multiplier=2.0, cap=60.0)
                if on_rate_rotate:
                    await on_rate_rotate()
            # -404: week not found → skip (not retryable)
            elif e.bili_code == -404:
                last_error = f"Week #{number} not found (code=-404)"
                print(f"  ⚠ {last_error}, skipping…")
                break  # exit retry loop immediately
            elif e.bili_code in (-403, -401):
                print(f"  ⚠ Week #{number}: auth failure (code={e.bili_code}), refreshing key…")
                new_key = await mixin_refresher(session)
                signer._key = new_key
            else:
                print(f"  ⚠ Week #{number}: Bilibili code={e.bili_code}, retrying…")
            if attempt < retries:
                await asyncio.sleep(_jitter(config.retry_delay))
            continue
        except HttpError as e:
            last_error = str(e)
            reqs_this_week += 1
            # HTTP 412: 风控 → 全局限流 + 刷新密钥
            if "412" in last_error:
                print(f"  🛡 Week #{number}: risk control (HTTP 412), refreshing key…")
                new_key = await mixin_refresher(session)
                signer._key = new_key
                if on_rate_hit:
                    await on_rate_hit(f"Week #{number} risk control (HTTP 412)",
                                     multiplier=3.0, cap=120.0)
            elif "403" in last_error or "401" in last_error:
                print(f"  ⚠ Week #{number}: HTTP {e.status}, refreshing WBI key…")
                new_key = await mixin_refresher(session)
                signer._key = new_key
            if attempt < retries:
                await asyncio.sleep(_jitter(config.retry_delay))
            continue

        # 成功前检测空响应
        if not data.get("list") and not data.get("config"):
            last_error = "HTTP 200: empty response"
            print(f"  ⚠ Week #{number}: empty response (attempt {attempt}/{retries}), "
                  f"refreshing key…")
            new_key = await mixin_refresher(session)
            signer._key = new_key
            if on_rate_hit:
                await on_rate_hit(f"Week #{number} empty response",
                                 multiplier=1.5, cap=30.0)
            if attempt < retries:
                await asyncio.sleep(_jitter(config.retry_delay))
            continue

        # 成功
        if on_success:
            await on_success()
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
