"""异步 HTTP 工具模块。函数式设计，Session 由调用方显式管理。"""
from typing import Any
import aiohttp
from bilianalysis.utils.ua import ua

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=3)


class HttpError(Exception):
    """HTTP 请求失败异常"""
    def __init__(self, status: int, message: str = "") -> None:
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}" if message else f"[{status}]")


def create_session(timeout: aiohttp.ClientTimeout | None = None) -> aiohttp.ClientSession:
    """创建预配置 Session：自动注入随机 UA header + 超时"""
    headers = {"User-Agent": ua.random}
    return aiohttp.ClientSession(headers=headers, timeout=timeout or DEFAULT_TIMEOUT)


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
        async with getattr(session, method)(
            url, headers=req_headers or None, data=data, json=json
        ) as resp:
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
