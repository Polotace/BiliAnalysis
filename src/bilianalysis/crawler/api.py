"""Bilibili "每周必看" API 封装。"""
from typing import Any
from urllib.parse import urlencode

import aiohttp
from bilianalysis.utils.fetch import get
from bilianalysis.crawler.signer import WbiSigner

BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"


async def list_series(
    session: aiohttp.ClientSession,
    signer: WbiSigner
) -> list[dict[str, Any]]:
    """获取所有期数列表。返回 data.list，按 number 升序排列。"""
    params = signer.sign({})
    url = f"{BASE_URL}/list?{urlencode(params)}"
    resp = await get(session, url)
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
    return resp.get("data", {})


if __name__ == '__main__':
    import asyncio
    from bilianalysis.crawler.signer import fetch_mixin_key, WbiSigner
    async def main():
        session = aiohttp.ClientSession()
        mixin_key = await fetch_mixin_key(session)
        signer = WbiSigner(mixin_key)
        series = await list_series(session, signer)
        print(series)
        if series:
            data = await get_weekly_videos(session, series[0]["number"], signer)
            print(data)
        await session.close()
    asyncio.run(main())