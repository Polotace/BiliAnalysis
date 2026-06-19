"""Database load endpoint: POST /api/db/load"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bilianalysis.config.model import AppConfig
from app.api.db.loader import load_incremental, load_raw_weeks
from app.api.deps import get_config, get_db

router = APIRouter(tags=["database"])


@router.post("/db/load")
async def load_to_db(
    config: Annotated[AppConfig, Depends(get_config)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Load raw week data from data/raw/ into PostgreSQL.

    Incremental — skips weeks already present in the database.
    Returns {loaded: [...], skipped: [...], failed: {...}}.
    """
    raw_records = load_raw_weeks(config.data.raw_dir)
    result = await load_incremental(session, raw_records)
    return result
