"""Integration tests for db/loader.py — requires PostgreSQL.

Set BILIINSIGHT_TEST_DB_URL env var to point at a test database.
Tests are skipped if no PostgreSQL is reachable.
"""
import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.db.schema import (
    Base, WeeklyModel, CreatorModel, CategoryModel,
    VideoModel, VideoStatModel, WeeklyVideoModel,
)
from api.db.loader import load_week, load_incremental
from bilianalysis.etl.transform import transform_week

TEST_DB_URL = os.environ.get(
    "BILIINSIGHT_TEST_DB_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/biliinsight_test",
)


async def _pg_is_reachable() -> bool:
    """Return True if the test database is reachable."""
    try:
        engine = create_async_engine(TEST_DB_URL)
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: None)
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def _pg_available():
    """Module-scoped check: skip all tests if PG is unreachable."""
    import asyncio
    if not asyncio.run(_pg_is_reachable()):
        pytest.skip("PostgreSQL not available", allow_module_level=True)


@pytest.fixture
async def pg_session(_pg_available):
    """Create tables, yield session, drop tables after."""
    engine = create_async_engine(TEST_DB_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def week1_records():
    """Load real week_001.json through transform_week."""
    import json
    from pathlib import Path
    raw = json.loads((Path("data/raw") / "week_001.json").read_text(encoding="utf-8"))
    return transform_week(raw)


@pytest.mark.asyncio
async def test_load_week_writes_all_tables(pg_session, week1_records):
    """load_week inserts records into all 6 tables."""
    async with pg_session.begin():
        await load_week(pg_session, week1_records)

    # Verify row counts — all 6 tables should have data
    from sqlalchemy import select, func
    tables = [WeeklyModel, CreatorModel, CategoryModel,
              VideoModel, VideoStatModel, WeeklyVideoModel]
    for model in tables:
        result = await pg_session.execute(select(func.count()).select_from(model))
        count = result.scalar()
        assert count > 0, f"{model.__tablename__} should have rows"


@pytest.mark.asyncio
async def test_load_incremental_skips_existing(pg_session, week1_records):
    """Second load_incremental call skips already-loaded weeks."""
    result1 = await load_incremental(pg_session, [week1_records])
    assert 1 in result1["loaded"]

    result2 = await load_incremental(pg_session, [week1_records])
    assert 1 in result2["skipped"]
    assert 1 not in result2["loaded"]


@pytest.mark.asyncio
async def test_load_week_idempotent(pg_session, week1_records):
    """Loading the same week twice does not duplicate data."""
    await load_week(pg_session, week1_records)
    await load_week(pg_session, week1_records)  # should not raise

    from sqlalchemy import select, func
    result = await pg_session.execute(select(func.count()).select_from(WeeklyModel))
    count = result.scalar()
    assert count == 1  # still one weekly row
