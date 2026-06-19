# PostgreSQL Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostgreSQL storage to BiliInsight — library-side data transform functions, FastAPI-side ORM schema, incremental DB loader, and a synchronous API endpoint.

**Architecture:** Pure library `src/bilianalysis/etl/transform.py` reads `data/raw/*.json` and converts to plain dicts (no DB imports). FastAPI `app/api/db/` holds SQLAlchemy ORM + Pydantic entities + async loader. `POST /api/db/load` glues them: reads via library, writes via async session. Per-week transactions, incremental by querying `weekly` table.

**Tech Stack:** SQLAlchemy 2.0 async, asyncpg, existing FastAPI + Pydantic Settings + AppConfig

---

### Task 1: Install Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add sqlalchemy and asyncpg to pyproject.toml**

Add to `[project] dependencies`:

```toml
"sqlalchemy[asyncio]>=2.0.0",
"asyncpg>=0.30.0",
```

Should be inserted near the other dependencies. After editing, the `dependencies` list will include these two additions.

- [ ] **Step 2: Run uv sync to install**

```bash
uv sync
```

Expected: installs sqlalchemy, asyncpg, and their transitive deps. No errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add sqlalchemy[asyncio] and asyncpg dependencies"
```

---

### Task 2: api/config.py — ApiSettings

**Files:**
- Create: `app/api/config.py`
- Test: None (config is Pydantic Settings, tested implicitly via integration)

- [ ] **Step 1: Create app/api/config.py**

```python
"""FastAPI application settings — database URL lives here, not in global config.yaml."""
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/biliinsight"
    database_pool_size: int = 5

    model_config = {"env_file": ".env"}
```

- [ ] **Step 2: Commit**

```bash
git add app/api/config.py
git commit -m "feat: add ApiSettings for PostgreSQL connection config"
```

---

### Task 3: app/api/db/schema.py — ORM Models + Pydantic Entities

**Files:**
- Create: `app/api/db/__init__.py`
- Create: `app/api/db/schema.py`

- [ ] **Step 1: Create app/api/db/__init__.py**

```python
"""PostgreSQL database layer — ORM models, Pydantic entities, and loader."""
```

- [ ] **Step 2: Create app/api/db/schema.py**

```python
"""SQLAlchemy ORM models and Pydantic entities for 6 PostgreSQL tables."""
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ═══ ORM Models ═══

class WeeklyModel(Base):
    __tablename__ = "weekly"

    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CreatorModel(Base):
    __tablename__ = "creator"

    mid: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    face: Mapped[str | None] = mapped_column(Text, nullable=True)


class CategoryModel(Base):
    __tablename__ = "category"

    tid: Mapped[int] = mapped_column(Integer, primary_key=True)
    tname: Mapped[str | None] = mapped_column(Text, nullable=True)
    tid_v2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tname_v2: Mapped[str | None] = mapped_column(Text, nullable=True)
    pid_v2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pid_name_v2: Mapped[str | None] = mapped_column(Text, nullable=True)


class VideoModel(Base):
    __tablename__ = "video"

    aid: Mapped[int] = mapped_column(Integer, primary_key=True)
    bvid: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubdate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    copyright: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creator_mid: Mapped[int | None] = mapped_column(ForeignKey("creator.mid"), nullable=True)
    category_tid: Mapped[int | None] = mapped_column(ForeignKey("category.tid"), nullable=True)


class VideoStatModel(Base):
    __tablename__ = "video_stat"

    aid: Mapped[int] = mapped_column(ForeignKey("video.aid"), primary_key=True)
    view: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    like_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    coin: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    favorite: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    share: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reply: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    danmaku: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class WeeklyVideoModel(Base):
    __tablename__ = "weekly_video"

    weekly_number: Mapped[int] = mapped_column(ForeignKey("weekly.number"), primary_key=True)
    aid: Mapped[int] = mapped_column(ForeignKey("video.aid"), primary_key=True)


# ═══ Pydantic Entities (used for validation in loader) ═══

class WeeklyEntity(BaseModel):
    number: int
    subject: str | None = None
    name: str | None = None
    label: str | None = None
    cover: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class CreatorEntity(BaseModel):
    mid: int
    name: str | None = None
    face: str | None = None


class CategoryEntity(BaseModel):
    tid: int
    tname: str | None = None
    tid_v2: int | None = None
    tname_v2: str | None = None
    pid_v2: int | None = None
    pid_name_v2: str | None = None


class VideoEntity(BaseModel):
    aid: int
    bvid: str | None = None
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    pubdate: datetime | None = None
    cid: int | None = None
    video_url: str | None = None
    cover_url: str | None = None
    copyright: int | None = None
    creator_mid: int | None = None
    category_tid: int | None = None


class VideoStatEntity(BaseModel):
    aid: int
    view: int | None = None
    like_cnt: int | None = None
    coin: int | None = None
    favorite: int | None = None
    share: int | None = None
    reply: int | None = None
    danmaku: int | None = None


class WeeklyVideoEntity(BaseModel):
    weekly_number: int
    aid: int
```

- [ ] **Step 3: Commit**

```bash
git add app/api/db/__init__.py app/api/db/schema.py
git commit -m "feat: add SQLAlchemy ORM models and Pydantic entities for 6 PostgreSQL tables"
```

---

### Task 4: src/bilianalysis/etl/transform.py — Library-side Data Conversion

**Files:**
- Create: `src/bilianalysis/etl/__init__.py`
- Create: `src/bilianalysis/etl/transform.py`

- [ ] **Step 1: Create src/bilianalysis/etl/__init__.py**

```python
"""ETL data transform utilities — pure functions, no DB access."""
from .transform import transform_week, load_raw_weeks

__all__ = ["transform_week", "load_raw_weeks"]
```

- [ ] **Step 2: Create src/bilianalysis/etl/transform.py**

```python
"""Pure data transformation: raw JSON dict → typed record dicts.

This module is the sole accessor of data/raw/. It MUST NOT import
sqlalchemy, asyncpg, or any other database driver.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _ts_to_datetime(ts: int | float) -> datetime:
    """Convert a UNIX timestamp to a timezone-aware datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def transform_week(raw: dict) -> dict[str, list[dict]]:
    """Convert a single week's raw JSON dict into 6 groups of plain dict records.

    Pure function — no file I/O, no DB imports.

    Returns:
        {
            "weekly":       [dict],   # 1-element list
            "creators":     [dict],   # deduped by mid within this week
            "categories":   [dict],   # deduped by tid within this week
            "videos":       [dict],
            "video_stats":  [dict],
            "weekly_videos": [dict],
        }
    """
    number = raw["number"]
    cfg = raw.get("config", {})
    videos = raw.get("videos", [])

    # Weekly
    weekly = [{
        "number": number,
        "subject": cfg.get("subject"),
        "name": cfg.get("name"),
        "label": cfg.get("label"),
        "cover": cfg.get("cover"),
        "start_time": _ts_to_datetime(cfg["stime"]) if "stime" in cfg else None,
        "end_time": _ts_to_datetime(cfg["etime"]) if "etime" in cfg else None,
    }]

    creators = []
    categories = []
    video_list = []
    video_stats = []
    weekly_videos = []

    seen_mids: set[int] = set()
    seen_tids: set[int] = set()

    for v in videos:
        owner = v.get("owner", {})
        stat = v.get("stat", {})

        mid = owner.get("mid")
        tid = v.get("tid")

        # Creator (dedup by mid)
        if mid is not None and mid not in seen_mids:
            seen_mids.add(mid)
            creators.append({
                "mid": mid,
                "name": owner.get("name"),
                "face": owner.get("face"),
            })

        # Category (dedup by tid)
        if tid is not None and tid not in seen_tids:
            seen_tids.add(tid)
            categories.append({
                "tid": tid,
                "tname": v.get("tname"),
                "tid_v2": v.get("tidv2"),
                "tname_v2": v.get("tnamev2"),
                "pid_v2": v.get("pid_v2"),
                "pid_name_v2": v.get("pid_name_v2"),
            })

        aid = v.get("aid")

        video_list.append({
            "aid": aid,
            "bvid": v.get("bvid"),
            "title": v.get("title"),
            "description": v.get("desc"),
            "duration": v.get("duration"),
            "pubdate": _ts_to_datetime(v["pubdate"]) if "pubdate" in v else None,
            "cid": v.get("cid"),
            "video_url": v.get("short_link_v2"),
            "cover_url": v.get("pic"),
            "copyright": v.get("copyright"),
            "creator_mid": mid,
            "category_tid": tid,
        })

        video_stats.append({
            "aid": stat.get("aid", aid),
            "view": stat.get("view"),
            "like_cnt": stat.get("like"),
            "coin": stat.get("coin"),
            "favorite": stat.get("favorite"),
            "share": stat.get("share"),
            "reply": stat.get("reply"),
            "danmaku": stat.get("danmaku"),
        })

        weekly_videos.append({
            "weekly_number": number,
            "aid": aid,
        })

    return {
        "weekly": weekly,
        "creators": creators,
        "categories": categories,
        "videos": video_list,
        "video_stats": video_stats,
        "weekly_videos": weekly_videos,
    }


def load_raw_weeks(raw_dir: str | Path) -> list[dict[str, list[dict]]]:
    """Read all week_*.json files from data/raw/, apply transform_week to each.

    Returns a list in week-number ascending order.

    This is the ONLY function in the codebase that reads from data/raw/.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("week_*.json"),
                   key=lambda p: int(p.stem.split("_")[1]))
    results: list[dict[str, list[dict]]] = []
    for fp in files:
        raw = json.loads(fp.read_text(encoding="utf-8"))
        results.append(transform_week(raw))
    return results
```

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/etl/__init__.py src/bilianalysis/etl/transform.py
git commit -m "feat: add etl/transform.py — raw JSON to typed records, sole data/ accessor"
```

---

### Task 5: app/api/deps.py — Add get_db Dependency

**Files:**
- Modify: `app/api/deps.py`

- [ ] **Step 1: Add get_db to app/api/deps.py**

Read the current file, then add the following imports at the top (after existing imports):

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.api.config import ApiSettings
```

Add the following module-level variables and functions before the existing `get_config` function:

```python
_engine = None
_sessionmaker = None


def _get_sessionmaker():
    """Lazy-init the async engine and sessionmaker from ApiSettings."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = ApiSettings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def get_db():
    """Yield an AsyncSession. Session lifecycle = request scope."""
    sm = _get_sessionmaker()
    async with sm() as session:
        yield session
```

The resulting file should have: `get_db`, `get_config`, `get_runner`, `get_engine` — in that order.

- [ ] **Step 2: Verify the file imports cleanly**

```bash
uv run python -c "from app.api.deps import get_db, get_config, get_runner, get_engine; print('OK')"
```

Expected: `OK` (no ImportError). Note: this won't actually connect to a database.

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add get_db dependency injection for async PostgreSQL sessions"
```

---

### Task 6: app/api/db/loader.py — Database Loader

**Files:**
- Create: `app/api/db/loader.py`

- [ ] **Step 1: Create app/api/db/loader.py**

```python
"""Incremental database loader for raw week records.

Consumes dict records produced by src/bilianalysis/etl/transform.py.
Does NOT read from data/ directly — only executes SQL.
"""
import logging

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.db.schema import (
    WeeklyModel, CreatorModel, CategoryModel, VideoModel,
    VideoStatModel, WeeklyVideoModel,
    WeeklyEntity, CreatorEntity, CategoryEntity, VideoEntity,
    VideoStatEntity, WeeklyVideoEntity,
)

logger = logging.getLogger(__name__)


async def load_week(
    pg_session: AsyncSession,
    records: dict[str, list[dict]],
) -> None:
    """Insert one week's records into all 6 tables within a single transaction.

    Insert order respects FK dependencies:
    weekly → creator → category → video → video_stat → weekly_video
    """
    async with pg_session.begin():
        # 1. weekly (single row, immutable)
        w = WeeklyEntity.model_validate(records["weekly"][0])
        await pg_session.execute(
            insert(WeeklyModel).values(w.model_dump()).on_conflict_do_nothing()
        )

        # 2. creators (immutable after first insert)
        for c in records["creators"]:
            ce = CreatorEntity.model_validate(c)
            await pg_session.execute(
                insert(CreatorModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 3. categories (immutable after first insert)
        for c in records["categories"]:
            ce = CategoryEntity.model_validate(c)
            await pg_session.execute(
                insert(CategoryModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 4. videos (update on conflict — same video may reappear with changes)
        for v in records["videos"]:
            ve = VideoEntity.model_validate(v)
            values = ve.model_dump()
            await pg_session.execute(
                insert(VideoModel).values(values).on_conflict_do_update(
                    index_elements=["aid"],
                    set_={k: v for k, v in values.items() if k != "aid"},
                )
            )

        # 5. video_stats (update on conflict — stats change across weeks)
        for vs in records["video_stats"]:
            vse = VideoStatEntity.model_validate(vs)
            values = vse.model_dump()
            await pg_session.execute(
                insert(VideoStatModel).values(values).on_conflict_do_update(
                    index_elements=["aid"],
                    set_={k: v for k, v in values.items() if k != "aid"},
                )
            )

        # 6. weekly_videos (immutable)
        for wv in records["weekly_videos"]:
            wve = WeeklyVideoEntity.model_validate(wv)
            await pg_session.execute(
                insert(WeeklyVideoModel).values(wve.model_dump()).on_conflict_do_nothing()
            )


async def load_incremental(
    pg_session: AsyncSession,
    all_records: list[dict[str, list[dict]]],
) -> dict:
    """Incremental load: query weekly table, skip existing weeks.

    Args:
        pg_session: Database session.
        all_records: Output of load_raw_weeks().

    Returns:
        {"loaded": [1, 2], "skipped": [3, 4], "failed": {5: "error message"}}
    """
    # Query existing week numbers
    result = await pg_session.execute(select(WeeklyModel.number))
    existing = {row[0] for row in result.all()}

    loaded: list[int] = []
    skipped: list[int] = []
    failed: dict[int, str] = {}

    for records in all_records:
        week_num = records["weekly"][0]["number"]

        if week_num in existing:
            skipped.append(week_num)
            continue

        try:
            await load_week(pg_session, records)
            loaded.append(week_num)
        except Exception as exc:
            logger.exception("Failed to load week %s: %s", week_num, exc)
            failed[week_num] = str(exc)

    return {"loaded": loaded, "skipped": skipped, "failed": failed}
```

- [ ] **Step 2: Commit**

```bash
git add app/api/db/loader.py
git commit -m "feat: add incremental PostgreSQL loader with per-week transactions"
```

---

### Task 7: app/api/router/db_load.py — API Endpoint

**Files:**
- Create: `app/api/router/db_load.py`

- [ ] **Step 1: Create app/api/router/db_load.py**

```python
"""Database load endpoint: POST /api/db/load"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bilianalysis.config.model import AppConfig
from bilianalysis.etl import load_raw_weeks
from app.api.db.loader import load_incremental
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
```

- [ ] **Step 2: Commit**

```bash
git add app/api/router/db_load.py
git commit -m "feat: add POST /api/db/load endpoint for incremental DB loading"
```

---

### Task 8: app/api/app.py — Register Router and Wire DDL

**Files:**
- Modify: `app/api/app.py`

- [ ] **Step 1: Add db_load router registration and DDL startup hook**

Read the current `app/api/app.py`. Two changes needed:

**Change A**: In the router registration block (after the existing 4 `include_router` lines), add:

```python
from app.api.router import db_load
app.include_router(db_load.router, prefix="/api")
```

**Change B**: Add a startup event handler that runs DDL. After the router registration block, before `_register_error_handlers(app)`, add:

```python
@app.on_event("startup")
async def _init_db():
    """Create tables if they don't exist."""
    from app.api.deps import _get_sessionmaker
    from app.api.db.schema import Base
    sm = _get_sessionmaker()
    async with sm() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
```

The complete router registration block should look like:

```python
# Register routes
from app.api.router import crawler, analysis, tasks, config as config_router
app.include_router(crawler.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(config_router.router, prefix="/api")

# Register db_load router
from app.api.router import db_load
app.include_router(db_load.router, prefix="/api")

@app.on_event("startup")
async def _init_db():
    """Create tables if they don't exist."""
    from app.api.deps import _get_sessionmaker
    from app.api.db.schema import Base
    sm = _get_sessionmaker()
    async with sm() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Verify the app still imports**

```bash
uv run python -c "from app.api.app import create_app; print('OK')"
```

Expected: `OK` (no ImportError).

- [ ] **Step 3: Commit**

```bash
git add app/api/app.py
git commit -m "feat: register db_load router and wire DDL on startup"
```

---

### Task 9: tests/test_transform.py — Unit Tests

**Files:**
- Create: `tests/test_transform.py`
- Use fixture: `data/raw/week_001.json`

- [ ] **Step 1: Create tests/test_transform.py**

```python
"""Unit tests for etl/transform.py — pure functions, no DB needed."""
import json
from datetime import datetime, timezone
from pathlib import Path

from bilianalysis.etl.transform import transform_week, load_raw_weeks

RAW_DIR = Path("data/raw")


def test_transform_week_produces_six_groups():
    """transform_week returns all 6 expected keys with correct types."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    assert set(result.keys()) == {
        "weekly", "creators", "categories",
        "videos", "video_stats", "weekly_videos",
    }
    # weekly is a single-element list
    assert len(result["weekly"]) == 1
    assert result["weekly"][0]["number"] == 1
    assert result["weekly"][0]["subject"] == "神仙爱情"
    assert result["weekly"][0]["label"] == "第1期(0329更新)"

    # at least one video
    assert len(result["videos"]) > 0

    # creator, video_stats, weekly_videos have same length as videos
    n = len(result["videos"])
    assert len(result["video_stats"]) == n
    assert len(result["weekly_videos"]) == n


def test_transform_week_dedup_creators():
    """Creators are deduped by mid within a single week."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    mids = [c["mid"] for c in result["creators"]]
    assert len(mids) == len(set(mids))  # no duplicates

    # week_001 has at least creator mid=546195 (老番茄)
    assert 546195 in mids


def test_transform_week_dedup_categories():
    """Categories are deduped by tid within a single week."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    tids = [c["tid"] for c in result["categories"]]
    assert len(tids) == len(set(tids))


def test_transform_week_unix_timestamps_become_datetime():
    """UNIX int timestamps are converted to timezone-aware datetime objects."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    w = result["weekly"][0]
    assert isinstance(w["start_time"], datetime)
    assert isinstance(w["end_time"], datetime)
    assert w["start_time"].tzinfo is not None

    v = result["videos"][0]
    assert isinstance(v["pubdate"], datetime)
    assert v["pubdate"].tzinfo is not None


def test_transform_week_field_mapping():
    """Spot-check that key fields map from raw JSON correctly."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    # First video: aid=46900196
    v = next(x for x in result["videos"] if x["aid"] == 46900196)
    assert v["bvid"] == "BV14b411J7ML"
    assert v["video_url"] == "https://b23.tv/BV14b411J7ML"
    assert v["copyright"] == 1
    assert v["creator_mid"] == 326257138
    assert v["category_tid"] == 250

    # Its stat
    vs = next(x for x in result["video_stats"] if x["aid"] == 46900196)
    assert vs["view"] == 5391512
    assert vs["like_cnt"] == 509422
    assert vs["coin"] == 553737
    assert vs["danmaku"] == 70080


def test_transform_week_empty_videos():
    """Week with no videos should return empty lists except weekly."""
    raw = {"number": 999, "config": {}, "videos": []}
    result = transform_week(raw)

    assert len(result["weekly"]) == 1
    assert result["videos"] == []
    assert result["creators"] == []
    assert result["categories"] == []
    assert result["video_stats"] == []
    assert result["weekly_videos"] == []


def test_transform_week_missing_optional_fields():
    """Videos with missing optional fields should get None values."""
    raw = {
        "number": 999,
        "config": {},
        "videos": [{
            "aid": 1,
            "stat": {},
            "owner": {},
        }]
    }
    result = transform_week(raw)

    v = result["videos"][0]
    assert v["bvid"] is None
    assert v["video_url"] is None
    assert v["copyright"] is None
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_transform.py -v
```

Expected: 7 passed. (week_001.json fixture exists in data/raw/)

- [ ] **Step 3: Commit**

```bash
git add tests/test_transform.py
git commit -m "test: add unit tests for transform_week field mapping and dedup"
```

---

### Task 10: tests/test_loader.py — Integration Tests

**Files:**
- Create: `tests/test_loader.py`

- [ ] **Step 1: Create tests/test_loader.py**

```python
"""Integration tests for db/loader.py — requires PostgreSQL."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.api.db.schema import Base, WeeklyModel, VideoModel, VideoStatModel
from app.api.db.loader import load_week, load_incremental
from bilianalysis.etl.transform import transform_week

# Use a real PG connection — skip if not available.
# Set BILIINSIGHT_TEST_DB_URL env var to point at a test database.
TEST_DB_URL = "postgresql+asyncpg://localhost:5432/biliinsight_test"


@pytest.fixture
async def pg_session():
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
    await load_week(pg_session, week1_records)

    # Verify row counts
    from sqlalchemy import select, func
    tables = [WeeklyModel, VideoModel, VideoStatModel]
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
```

- [ ] **Step 2: Run with a test database (optional — needs PG)**

```bash
# Only run if you have a local test PG:
# uv run pytest tests/test_loader.py -v -s
#
# Otherwise skip — these tests require a PG instance.
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_loader.py
git commit -m "test: add integration tests for PostgreSQL loader"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run all existing tests to ensure no regressions**

```bash
uv run pytest tests/ -v --ignore=tests/test_loader.py --ignore=tests/test_transform.py -k "not loader and not transform"
```

Expected: All 109 existing tests pass.

- [ ] **Step 2: Run new unit tests**

```bash
uv run pytest tests/test_transform.py -v
```

Expected: 7 passed.

- [ ] **Step 3: Verify the app creates with full router set**

```bash
uv run python -c "
from bilianalysis.config import load_config
from app.api.app import create_app
config = load_config()
app = create_app(config)
routes = [r.path for r in app.routes]
print([r for r in routes if 'db' in r or 'load' in r])
"
```

Expected: Shows `['/api/db/load']` in the output.

- [ ] **Step 4: Commit any remaining changes**

```bash
git status
```

If clean, done. If not, commit remaining files.
