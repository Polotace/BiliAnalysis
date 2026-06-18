"""WBI 签名模块：fetch_mixin_key + WbiSigner。"""
import hashlib
import time
from typing import Any
from urllib.parse import urlencode

import aiohttp
from bilianalysis.utils.fetch import get

MIXIN_TABLE = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
               27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
               37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
               22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44, 34]

WEB_LOCATION = "333.934"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
BILI_HEADER = {
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def fetch_mixin_key(session: aiohttp.ClientSession) -> str:
    """从 nav 接口获取 img_key + sub_key，计算 mixin_key。"""
    resp = await get(session, NAV_URL, headers=BILI_HEADER)
    wbi_img: dict[str, str] = resp.get("data", {}).get("wbi_img", {})
    img_url: str = wbi_img.get("img_url", "")
    sub_url: str = wbi_img.get("sub_url", "")

    # 从 URL 提取文件名，去掉路径和 .png 后缀
    img_key = img_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    sub_key = sub_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    raw = img_key + sub_key
    mixin = "".join(raw[i] for i in MIXIN_TABLE[:32])
    return mixin


class WbiSigner:
    """WBI 签名器。持有 mixin_key，提供 sign(params) 方法。"""

    def __init__(self, mixin_key: str):
        self._key = mixin_key

    def sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """对参数追加 wts + web_location + w_rid 后返回完整参数字典。"""
        signed: dict[str, Any] = dict(params)
        signed["wts"] = str(int(time.time()))
        signed["web_location"] = WEB_LOCATION
        signed["w_rid"] = self._compute_wrid(signed)
        return signed

    def _compute_wrid(self, params: dict[str, Any]) -> str:
        sorted_items = sorted(params.items(), key=lambda x: x[0])
        qs = urlencode(sorted_items)
        return hashlib.md5((qs + self._key).encode()).hexdigest()
