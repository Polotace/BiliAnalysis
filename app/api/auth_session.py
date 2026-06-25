"""Session helpers: get_current_user, require_admin, require_login."""
import secrets
from typing import Annotated
from fastapi import Request, Depends, HTTPException


def get_current_user(request: Request) -> dict | None:
    return request.session.get("user")


def require_admin(
    request: Request,
    user: Annotated[dict | None, Depends(get_current_user)],
):
    # Session-based auth
    if user is not None and user.get("role") == "admin":
        return user
    # Fallback: X-API-Key header (backward compat)
    expected = request.app.state.api_settings.admin_api_key
    provided = request.headers.get("X-API-Key", "")
    if provided and secrets.compare_digest(provided, expected):
        return {"role": "admin", "username": "api_key"}
    # Neither worked
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    raise HTTPException(status_code=403, detail="需要管理员权限")


def require_login(user: Annotated[dict | None, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user
