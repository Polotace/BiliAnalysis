"""Bilibili API 封装。"""
from typing import Any
from urllib.parse import urlencode

import aiohttp
from bilianalysis.utils.fetch import get, BiliCodeError
from bilianalysis.crawler.signer import WbiSigner

BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"
RELATION_URL = "https://api.bilibili.com/x/relation/stat"


def _check_bili_code(resp: dict, url: str) -> None:
    """检查 B站响应中的业务 code 字段。非 0 则抛 BiliCodeError。"""
    code = resp.get("code", 0)
    if code != 0:
        msg = resp.get("message", "")
        raise BiliCodeError(200, code, f"{url} → {msg}" if msg else url)


async def list_series(
    session: aiohttp.ClientSession,
    signer: WbiSigner
) -> list[dict[str, Any]]:
    """获取所有期数列表。返回 data.list，按 number 升序排列。"""
    params = signer.sign({})
    url = f"{BASE_URL}/list?{urlencode(params)}"
    resp = await get(session, url)
    _check_bili_code(resp, url)
    items: list[dict[str, Any]] = resp.get("data", {}).get("list", [])
    items.sort(key=lambda x: x.get("number", 0))
    return items


async def get_weekly_videos(
    session: aiohttp.ClientSession,
    number: int,
    signer: WbiSigner
) -> dict[str, Any]:
    """获取指定期数的完整数据。返回 API 原始 data 字典 {config, list}。
       HttpError 直接透传，由 pipeline 层捕获处理。"""
    params = signer.sign({"number": str(number)})
    url = f"{BASE_URL}/one?{urlencode(params)}"
    resp = await get(session, url)
    _check_bili_code(resp, url)
    return resp.get("data", {})


async def get_creator_relation_stats(
    session: aiohttp.ClientSession,
    mid: int,
) -> dict[str, Any]:
    """获取 UP 主关注/粉丝数。无需 WBI 签名，风控要求低。

    返回 data 字段包含: mid, following, follower
    """
    url = f"{RELATION_URL}?vmid={mid}&web_location=333.1387"
    resp = await get(session, url)
    _check_bili_code(resp, url)
    return resp.get("data", {})

