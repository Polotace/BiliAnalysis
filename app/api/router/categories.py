"""Category list endpoint: /api/categories"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.queries import get_categories
from api.deps import get_db

router = APIRouter(tags=["categories"])


@router.get("/categories")
async def list_categories(session: Annotated[AsyncSession, Depends(get_db)]):
    """Return all categories with video counts, ordered by count descending."""
    return await get_categories(session)
