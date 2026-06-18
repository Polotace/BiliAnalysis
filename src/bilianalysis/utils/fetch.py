"""异步 HTTP 工具模块。函数式设计，Session 由调用方显式管理。"""
import random
import string
import time
from typing import Any
import aiohttp
from .ua import ua

__all__ = ["HttpError", "BiliCodeError", "create_session", "get", "post",
           "make_device_cookie"]

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=3)

# ── Header rotation pools ──
_REFERERS = [
    "https://www.bilibili.com/",
    "https://www.bilibili.com/v/popular/weekly",
    "https://www.bilibili.com/v/popular/weekly/1",
    "https://www.bilibili.com/v/popular/rank/all",
]
_ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.6",
]


class HttpError(Exception):
    """HTTP 请求失败异常"""
    def __init__(self, status: int, message: str = "") -> None:
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}" if message else f"[{status}]")


class BiliCodeError(HttpError):
    """B站业务层面错误（code != 0 或特定错误码）"""
    def __init__(self, status: int, bili_code: int, message: str = "") -> None:
        self.bili_code = bili_code
        super().__init__(status, f"code={bili_code} {message}")


def make_device_cookie() -> str:
    """生成模拟真机首次访问 B站的设备指纹 Cookie。
    包含 buvid3（32位 hex）、buvid4（36位 UUID）、b_lsid（会话 ID）。
    每次调用生成一个新设备身份。"""
    buvid3 = ''.join(random.choices(string.hexdigits.lower(), k=32))
    buvid4 = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    blsid = ''.join(random.choices(string.hexdigits.lower(), k=16))
    # 模拟首次访问的时间戳
    ts = int(time.time())
    return (
        f"buvid3={buvid3}; buvid4={buvid4}; b_lsid={blsid}; "
        f"b_nut={ts}; _uuid={buvid4.upper()}-infoc"
    )


def _random_headers(cookie: str = "") -> dict[str, str]:
    """生成带随机 Referer + Accept-Language 的请求头。"""
    h = {
        "User-Agent": ua.random,
        "Referer": random.choice(_REFERERS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
    }
    if cookie:
        h["Cookie"] = cookie
    return h


def create_session(
    timeout: aiohttp.ClientTimeout | None = None,
    cookie: str = "",
) -> aiohttp.ClientSession:
    """创建预配置 Session：设备指纹 Cookie + 随机 UA + Referer + Accept-Language。"""
    device = make_device_cookie()
    full_cookie = f"{device}; {cookie}" if cookie else device
    return aiohttp.ClientSession(
        headers=_random_headers(full_cookie),
        timeout=timeout or DEFAULT_TIMEOUT,
        cookie_jar=aiohttp.CookieJar(),  # 接受服务端 set-cookie（如果有）
    )


def rotate_session_headers(session: aiohttp.ClientSession, cookie: str = "") -> None:
    """轮换 Session 的请求头（更换设备指纹 + UA + Referer）。"""
    device = make_device_cookie()
    full_cookie = f"{device}; {cookie}" if cookie else device
    session.headers.clear()
    session.headers.update(_random_headers(full_cookie))


async def _request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    json: Any = None,
) -> Any:
    """内部方法：发送 HTTP 请求并解析响应。"""
    req_headers = dict(headers) if headers else {}
    try:
        kwargs = {"headers": req_headers or None}
        if method in ("post", "put", "patch"):
            kwargs["data"] = data
            kwargs["json"] = json
        async with getattr(session, method)(url, **kwargs) as resp:
            if resp.status == 200:
                content_type = resp.content_type or ""
                if "application/json" in content_type:
                    return await resp.json()
                return await resp.text()
            raise HttpError(resp.status, await resp.text())
    except aiohttp.ClientError as e:
        raise HttpError(0, str(e))


async def get(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET 请求。JSON 响应解析为 dict/list；非 JSON 返回文本。失败抛 HttpError。"""
    return await _request(session, "get", url, headers=headers)


async def post(
    session: aiohttp.ClientSession,
    url: str,
    data: dict[str, Any] | None = None,
    json: Any = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """POST 请求。JSON 响应解析为 dict/list；非 JSON 返回文本。失败抛 HttpError。"""
    return await _request(session, "post", url, headers=headers, data=data, json=json)
