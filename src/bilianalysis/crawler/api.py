"""Bilibili "每周必看" API 封装。"""
from typing import Any
import aiohttp
from bilianalysis.utils.fetch import get

BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"


async def list_series(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """获取所有期数列表。返回 data.list，按 number 升序排列。"""
    url = f"{BASE_URL}/list"
    resp = await get(session, url)
    items: list[dict[str, Any]] = resp.get("data", {}).get("list", [])
    items.sort(key=lambda x: x.get("number", 0))
    return items


async def get_weekly_videos(
    session: aiohttp.ClientSession, number: int
) -> dict[str, Any]:
    """获取指定期数的完整数据。返回 API 原始 data 字典 {config, list}。
       HttpError 直接透传，由 pipeline 层捕获处理。"""
    url = f"{BASE_URL}/one?number={number}"
    resp = await get(session, url)
    return resp.get("data", {})
