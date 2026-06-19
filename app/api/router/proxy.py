"""Image proxy endpoint — fetches Bilibili CDN images with proper Referer."""
import logging
from typing import Annotated

import httpx2 as httpx
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["proxy"])

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

# Known Bilibili CDN domains that check Referer
_ALLOWED_HOSTS = {
    "i0.hdslb.com", "i1.hdslb.com", "i2.hdslb.com",
    "archive.biliimg.com", "pic.rmb.bdstatic.com",
}


@router.get("/proxy/image")
async def proxy_image(url: Annotated[str, Query(description="Original image URL")]):
    """Fetch an image from Bilibili's CDN with proper Referer headers.

    Bilibili's CDN returns 403 if the Referer is not bilibili.com.
    This proxy fetches the image server-side and returns it to the browser.
    """
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    if host not in _ALLOWED_HOSTS:
        # Allow other hosts too, but log a warning
        logger.debug("Proxying image from non-listed host: %s", host)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, headers=BILI_HEADERS, follow_redirects=True)
            if resp.status_code != 200:
                raise HTTPException(502, f"Upstream returned {resp.status_code}")

            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "Upstream timeout")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Upstream error: {e}")
