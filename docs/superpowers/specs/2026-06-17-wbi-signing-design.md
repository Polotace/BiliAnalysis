# WBI 签名 API 策略设计

Date: 2026-06-17 | Status: approved

## 概述

修改 Bilibili API 访问策略，为标准 WBI 签名机制添加 `web_location`、`w_rid`、`wts` 三个查询参数，替换当前的裸 GET 请求。

## 签名机制

Bilibili WBI (Web Interface) 标准签名流程：

1. 从 `https://api.bilibili.com/x/web-interface/nav` 获取 `data.wbi_img.img_url` 和 `data.wbi_img.sub_url`
2. 从 URL 文件名提取 `img_key` 和 `sub_key`（去路径前缀和 `.png` 后缀）
3. 拼接 `img_key + sub_key`，按固定 `MIXIN_TABLE` 前 32 位重排得到 `mixin_key`
4. 每次请求：参数按 key 字母序排序 → 拼 query string → `md5(query_string + mixin_key)` → 填入 `w_rid`

## 文件结构

```
新增: src/bilianalysis/crawler/signer.py    # WbiSigner + fetch_mixin_key()

修改: src/bilianalysis/crawler/api.py       # list_series / get_weekly_videos 添加 signer 参数
修改: src/bilianalysis/crawler/pipeline.py  # run() 开头获取 mixin_key，下传到各 API 调用
修改: tests/test_api.py                     # 适配 signer 参数
修改: tests/test_pipeline.py               # 适配 signer 参数
```

## signer.py 模块

```python
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


async def fetch_mixin_key(session: aiohttp.ClientSession) -> str:
    """从 nav 接口获取 img_key + sub_key，计算 mixin_key。"""
    resp = await get(session, NAV_URL)
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
```

- `MIXIN_TABLE` — Bilibili 前端 JS 固定的 64 位索引数组
- `fetch_mixin_key()` — 独立 async 函数，函数式风格与 fetch.py 一致
- `WbiSigner.sign()` — 自动插入 `wts`（当前 Unix 时间戳）、`web_location` 固定值、计算 `w_rid`
- `sign()` 返回完整参数字典，调用方用 `urlencode()` 拼到 URL

## api.py 修改

```python
from bilianalysis.crawler.signer import WbiSigner
from urllib.parse import urlencode

async def list_series(
    session: aiohttp.ClientSession, signer: WbiSigner
) -> list[dict[str, Any]]:
    params = signer.sign({})
    url = f"{BASE_URL}/list?{urlencode(params)}"
    resp = await get(session, url)
    items: list[dict[str, Any]] = resp.get("data", {}).get("list", [])
    items.sort(key=lambda x: x.get("number", 0))
    return items


async def get_weekly_videos(
    session: aiohttp.ClientSession, number: int, signer: WbiSigner
) -> dict[str, Any]:
    params = signer.sign({"number": str(number)})
    url = f"{BASE_URL}/one?{urlencode(params)}"
    resp = await get(session, url)
    return resp.get("data", {})
```

## pipeline.py 修改

| 位置 | 改动 |
|------|------|
| 新增导入 | `from .signer import fetch_mixin_key, WbiSigner` |
| `run()` 调用 `list_series` | `list_series(session)` → `list_series(session, signer)` |
| `run()` retry phase `get_weekly_videos` | 追加 `signer` 参数 |
| `_crawl_one` 签名 | 新增 `signer: WbiSigner` 参数 |
| `_crawl_one` 内部 `get_weekly_videos` | 追加 `signer` 参数 |

concurrent 模式 `crawl_with_semaphore` 闭包自动捕获外部 `signer` 引用，无需额外改动。

## 不在范围内

- 不做 mixin_key 缓存/定时刷新（每次 `run()` 重新获取）
- 不改 `fetch.py` 的 `get()` 函数签名（签名参数走 URL query string，非 header）
- 不修改 `config/` 配置模块
