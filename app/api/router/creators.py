"""Creator list/detail endpoints: /api/creators"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.queries import get_creators, get_creator
from api.deps import get_db
from bilianalysis.utils.fetch import create_session
from bilianalysis.crawler.api import get_creator_relation_stats

router = APIRouter(tags=["creators"])


@router.get("/creators")
async def list_creators(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("video_count", pattern="^(video_count|total_views|name)$", description="Sort field"),
):
    """Return a paginated, sortable list of creators with aggregated stats."""
    return await get_creators(
        session,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )


@router.get("/creators/{mid}")
async def show_creator(
    mid: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Return a single creator profile + aggregate stats + their videos, or 404."""
    detail = await get_creator(session, mid)
    if detail is None:
        raise HTTPException(404, f"Creator {mid} not found")
    return detail


@router.get("/creators/{mid}/stats")
async def creator_live_stats(mid: int):
    """Fetch live follower/following count from Bilibili API."""
    session = create_session()
    try:
        data = await get_creator_relation_stats(session, mid)
        return data
    finally:
        await session.close()
