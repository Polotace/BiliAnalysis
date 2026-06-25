"""Auth endpoints: login, logout, me, change-password."""
from typing import Annotated
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from api.auth import authenticate, hash_password, verify_password, get_user_by_username
from api.config import ApiSettings

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    logged_in: bool
    username: str | None = None
    role: str | None = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/login")
async def login(req: LoginRequest, request: Request,
                db: Annotated[AsyncSession, Depends(get_db)]):
    settings = ApiSettings()
    user = await authenticate(db, req.username, req.password, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    request.session["user"] = {
        "id": user.id, "username": user.username,
        "role": user.role, "must_change_password": user.must_change_password,
    }
    return {"ok": True, "must_change_password": user.must_change_password}


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/auth/me", response_model=UserInfo)
async def me(request: Request):
    u = request.session.get("user")
    if u is None:
        return UserInfo(logged_in=False)
    return UserInfo(logged_in=True, username=u["username"], role=u["role"],
                    must_change_password=u.get("must_change_password", False))


@router.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)]):
    u = request.session.get("user")
    if u is None:
        raise HTTPException(status_code=401)
    user = await get_user_by_username(db, u["username"])
    if user is None or not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password_hash = hash_password(req.new_password)
    user.must_change_password = False
    await db.commit()
    request.session["user"]["must_change_password"] = False
    return {"ok": True}
