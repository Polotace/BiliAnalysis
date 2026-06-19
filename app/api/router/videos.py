"""Video list/detail endpoints: /api/videos"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.queries import get_videos, get_video
from api.deps import get_db

router = APIRouter(tags=["videos"])


@router.get("/videos")
async def list_videos(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    week_number: int | None = Query(None, description="Filter by weekly number"),
    category_tid: int | None = Query(None, description="Filter by category TID"),
    creator_mid: int | None = Query(None, description="Filter by creator MID"),
    search: str | None = Query(None, description="Search in video title"),
    sort_by: str = Query("view", pattern="^(view|like|pubdate)$", description="Sort field"),
):
    """Return a paginated, filterable, sortable list of videos."""
    return await get_videos(
        session,
        page=page,
        page_size=page_size,
        week_number=week_number,
        category_tid=category_tid,
        creator_mid=creator_mid,
        search=search,
        sort_by=sort_by,
    )


@router.get("/videos/{aid}")
async def show_video(
    aid: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Return full video details or 404."""
    detail = await get_video(session, aid)
    if detail is None:
        raise HTTPException(404, f"Video {aid} not found")
    return detail
