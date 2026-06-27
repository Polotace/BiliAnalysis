"""Session helpers: get_current_user, require_admin, require_login."""
from typing import Annotated
from fastapi import Request, Depends, HTTPException


def get_current_user(request: Request) -> dict | None:
    return request.session.get("user")


def require_admin(user: Annotated[dict | None, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_login(user: Annotated[dict | None, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user
