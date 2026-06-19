"""Week list/detail endpoints: /api/weeks"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.queries import get_weeks, get_week
from api.deps import get_db

router = APIRouter(tags=["weeks"])


@router.get("/weeks")
async def list_weeks(session: Annotated[AsyncSession, Depends(get_db)]):
    """Return all weekly issues with video counts, newest first."""
    return await get_weeks(session)


@router.get("/weeks/{number}")
async def show_week(
    number: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Return a single week with its videos, or 404."""
    detail = await get_week(session, number)
    if detail is None:
        raise HTTPException(404, f"Week {number} not found")
    return detail
