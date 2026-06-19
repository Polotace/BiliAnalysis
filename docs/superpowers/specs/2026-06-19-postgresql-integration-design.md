# PostgreSQL Integration Design Spec

> 状态：待实现 | 撰写日期：2026-06-19 | 基于 `docs/new-scheme.md` §四/§六

## 1. Scope

本 spec 覆盖 4 个交付物：

1. `src/bilianalysis/etl/transform.py` — 库模块文件读取 + 纯转换函数
2. `app/api/db/schema.py` — SQLAlchemy ORM 模型 + Pydantic Entity + DDL
3. `app/api/db/loader.py` — 增量数据库写入
4. `app/api/router/db_load.py` — 同步加载端点 + `app/api/config.py`（数据库配置）+ `app/api/deps.py`（get_db 注入）

## 2. File Layout

```
src/bilianalysis/etl/          # ★ 新增
├── __init__.py
└── transform.py               # transform_week() + load_raw_weeks()

app/api/
├── config.py                   # ★ 新增：ApiSettings（database_url + pool_size）
├── deps.py                     # ★ 修改：+ get_db()
├── db/                         # ★ 新增
│   ├── __init__.py
│   ├── schema.py               #   ORM + Pydantic Entity
│   └── loader.py               #   load_incremental() + load_week()
└── router/
    └── db_load.py              # ★ 新增：POST /api/db/load
```

## 3. Schema Design

### 3.1 Tables (6)

```sql
-- weekly: 周刊信息
CREATE TABLE weekly (
    number     INTEGER PRIMARY KEY,   -- 期号
    subject    TEXT,                   -- 当期主题
    name       TEXT,                   -- 当期名称
    label      TEXT,                   -- 展示标签，如"第1期(0329更新)"
    cover      TEXT,                   -- 周刊封面图 URL
    start_time TIMESTAMPTZ,           -- 当周起始
    end_time   TIMESTAMPTZ            -- 当周结束
);

-- creator: UP 主
CREATE TABLE creator (
    mid  INTEGER PRIMARY KEY,         -- B站 UP 主 ID
    name TEXT,                         -- 昵称
    face TEXT                          -- 头像 URL
);

-- category: 三级分类
CREATE TABLE category (
    tid         INTEGER PRIMARY KEY,  -- 三级分类 ID
    tname       TEXT,                  -- 三级名
    tid_v2      INTEGER,              -- 二级分类 ID
    tname_v2    TEXT,                  -- 二级名
    pid_v2      INTEGER,              -- 一级分类 ID
    pid_name_v2 TEXT                   -- 一级名
);

-- video: 视频
CREATE TABLE video (
    aid          INTEGER PRIMARY KEY, -- AV 号
    bvid         TEXT,                -- BV 号
    title        TEXT,                -- 标题
    description  TEXT,                -- 简介
    duration     INTEGER,            -- 时长（秒）
    pubdate      TIMESTAMPTZ,        -- 发布时间
    cid          INTEGER,            -- CID
    video_url    TEXT,               -- short_link_v2
    cover_url    TEXT,               -- 封面图 URL
    copyright    INTEGER,            -- 1=原创 2=转载
    creator_mid  INTEGER REFERENCES creator(mid),
    category_tid INTEGER REFERENCES category(tid)
);

-- video_stat: 视频统计 (1:1 video)
CREATE TABLE video_stat (
    aid      INTEGER PRIMARY KEY REFERENCES video(aid),
    view     BIGINT,                   -- 播放量
    like_cnt BIGINT,                   -- 点赞数
    coin     BIGINT,                   -- 投币数
    favorite BIGINT,                   -- 收藏数
    share    BIGINT,                   -- 分享数
    reply    BIGINT,                   -- 评论数
    danmaku  BIGINT                    -- 弹幕数
);

-- weekly_video: 周刊-视频关联 (N:M)
CREATE TABLE weekly_video (
    weekly_number INTEGER REFERENCES weekly(number),
    aid           INTEGER REFERENCES video(aid),
    PRIMARY KEY (weekly_number, aid)
);
```

### 3.2 ORM + Pydantic Entity

- **SQLAlchemy ORM**：`WeeklyModel`, `CreatorModel`, `CategoryModel`, `VideoModel`, `VideoStatModel`, `WeeklyVideoModel`，用 `Mapped[]` + `mapped_column()` 风格
- **Pydantic Entity**：`WeeklyEntity`, `CreatorEntity`, `CategoryEntity`, `VideoEntity`, `VideoStatEntity`, `WeeklyVideoEntity` — 与 ORM 一一对应，`loader.py` 用 `WeeklyEntity(**dict)` 校验后写入
- `Base = DeclarativeBase` — 单一 `Base` 实例
- DDL：`async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)` 在启动时执行

### 3.3 Field Mapping: raw JSON → Records

#### weekly (single element list)

| Record Field | Raw Path |
|-------------|----------|
| number | `raw["number"]` |
| subject | `raw["config"]["subject"]` |
| name | `raw["config"]["name"]` |
| label | `raw["config"]["label"]` |
| cover | `raw["config"]["cover"]` |
| start_time | `raw["config"]["stime"]` (unix → datetime) |
| end_time | `raw["config"]["etime"]` (unix → datetime) |

#### creators (deduped by mid)

| Record Field | Raw Path |
|-------------|----------|
| mid | `v["owner"]["mid"]` |
| name | `v["owner"]["name"]` |
| face | `v["owner"]["face"]` |

#### categories (deduped by tid)

| Record Field | Raw Path |
|-------------|----------|
| tid | `v["tid"]` |
| tname | `v["tname"]` |
| tid_v2 | `v["tidv2"]` |
| tname_v2 | `v["tnamev2"]` |
| pid_v2 | `v["pid_v2"]` |
| pid_name_v2 | `v["pid_name_v2"]` |

#### videos

| Record Field | Raw Path |
|-------------|----------|
| aid | `v["aid"]` |
| bvid | `v["bvid"]` |
| title | `v["title"]` |
| description | `v["desc"]` |
| duration | `v["duration"]` |
| pubdate | `v["pubdate"]` (unix → datetime) |
| cid | `v["cid"]` |
| video_url | `v["short_link_v2"]` |
| cover_url | `v["pic"]` |
| copyright | `v["copyright"]` |
| creator_mid | `v["owner"]["mid"]` |
| category_tid | `v["tid"]` |

#### video_stats

| Record Field | Raw Path |
|-------------|----------|
| aid | `v["stat"]["aid"]` |
| view | `v["stat"]["view"]` |
| like_cnt | `v["stat"]["like"]` |
| coin | `v["stat"]["coin"]` |
| favorite | `v["stat"]["favorite"]` |
| share | `v["stat"]["share"]` |
| reply | `v["stat"]["reply"]` |
| danmaku | `v["stat"]["danmaku"]` |

#### weekly_videos

| Record Field | Raw Path |
|-------------|----------|
| weekly_number | `raw["number"]` |
| aid | `v["aid"]` |

## 4. Library Module: `src/bilianalysis/etl/transform.py`

### 4.1 Interface

```python
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

def load_raw_weeks(raw_dir: str | Path) -> list[dict[str, list[dict]]]:
    """Read all week_*.json files from data/raw/, apply transform_week to each.
    
    Returns a list in file-order (week number ascending).
    
    This is the ONLY function in the codebase that reads from data/raw/.
    """
```

### 4.2 `transform_week` Logic

1. Extract `number` and `config` from raw dict
2. Build weekly record: `{number, subject, name, label, cover, start_time, end_time}`
3. For each video in `raw["videos"]`:
   - Build creator record (track seen `mid`s, skip duplicates)
   - Build category record (track seen `tid`s, skip duplicates)
   - Build video record
   - Build video_stat record
   - Build weekly_video record
4. Return 6 lists

### 4.3 `load_raw_weeks` Logic

1. `glob` `week_*.json` from `raw_dir`, sorted by week number ascending
2. For each file: `json.loads(fp.read_text(...))` → `transform_week(dict)`
3. Return `list[dict[str, list[dict]]]`

### 4.4 UNIX Timestamp Handling

`start_time`, `end_time`, and `pubdate` arrive as UNIX timestamps (int). Convert to `datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()` so both Pydantic Entity and SQLAlchemy accept them.

## 5. Database Loader: `app/api/db/loader.py`

### 5.1 Interface

```python
async def load_week(
    pg_session: AsyncSession,
    records: dict[str, list[dict]],
) -> None:
    """Insert one week's records into all 6 tables within a single transaction."""

async def load_incremental(
    pg_session: AsyncSession,
    all_records: list[dict[str, list[dict]]],
) -> dict:
    """Incremental load: query weekly table, skip existing weeks.
    
    Returns:
        {"loaded": [1, 2], "skipped": [3, 4], "failed": {5: "error msg"}}
    """
```

### 5.2 `load_week` Logic

```python
async def load_week(pg_session: AsyncSession, records: dict[str, list[dict]]) -> None:
    async with pg_session.begin():
        # 1. weekly (single row)
        w = WeeklyEntity.model_validate(records["weekly"][0])
        await pg_session.execute(
            insert(WeeklyModel).values(w.model_dump()).on_conflict_do_nothing()
        )

        # 2. creators
        for c in records["creators"]:
            ce = CreatorEntity.model_validate(c)
            await pg_session.execute(
                insert(CreatorModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 3. categories
        for c in records["categories"]:
            ce = CategoryEntity.model_validate(c)
            await pg_session.execute(
                insert(CategoryModel).values(ce.model_dump()).on_conflict_do_nothing()
            )

        # 4. videos
        for v in records["videos"]:
            ve = VideoEntity.model_validate(v)
            await pg_session.execute(
                insert(VideoModel).values(ve.model_dump()).on_conflict_do_update(
                    index_elements=["aid"],
                    set_=ve.model_dump(exclude={"aid"}),
                )
            )

        # 5. video_stats
        for vs in records["video_stats"]:
            vse = VideoStatEntity.model_validate(vs)
            await pg_session.execute(
                insert(VideoStatModel).values(vse.model_dump()).on_conflict_do_update(
                    index_elements=["aid"],
                    set_=vse.model_dump(exclude={"aid"}),
                )
            )

        # 6. weekly_videos
        for wv in records["weekly_videos"]:
            wve = WeeklyVideoEntity.model_validate(wv)
            await pg_session.execute(
                insert(WeeklyVideoModel).values(wve.model_dump()).on_conflict_do_nothing()
            )
```

**Key decisions**:
- `creator`/`category`/`weekly_video`: `on_conflict_do_nothing` — immutable after first insert
- `video`/`video_stat`: `on_conflict_do_update` — same video may appear in multiple weeks with updated stats
- `weekly`: `on_conflict_do_nothing` — immutable

### 5.3 `load_incremental` Logic

1. `SELECT number FROM weekly` → `existing` set
2. For each `records` in `all_records`:
   - Extract `week_num = records["weekly"][0]["number"]`
   - If `week_num in existing` → `skipped`
   - Else: try `load_week(session, records)` → `loaded` on success, `failed` on exception
3. Return `{loaded, skipped, failed}`

## 6. Endpoint: `app/api/router/db_load.py`

### 6.1 Route

```
POST /api/db/load    # synchronous, returns result directly
```

### 6.2 Behavior

```python
@router.post("/db/load")
async def load_to_db(
    config: Annotated[AppConfig, Depends(get_config)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    raw_records = load_raw_weeks(config.data.raw_dir)
    result = await load_incremental(session, raw_records)
    return result
```

No background task. No run history. No `/status` endpoint. Synchronous call, returns `{loaded, skipped, failed}`.

## 7. Configuration: `app/api/config.py`

```python
from pydantic_settings import BaseSettings

class ApiSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/biliinsight"
    database_pool_size: int = 5

    model_config = {"env_file": ".env"}
```

Not in global `config.yaml`. This is FastAPI's private configuration.

## 8. Dependency Injection: `app/api/deps.py`

Add:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.api.config import ApiSettings

_engine = None
_sessionmaker = None

def _get_sessionmaker():
    global _engine, _sessionmaker
    if _engine is None:
        settings = ApiSettings()
        _engine = create_async_engine(settings.database_url, pool_size=settings.database_pool_size)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker

async def get_db():
    """Yield an AsyncSession for the request. Session lifecycle = request scope."""
    sm = _get_sessionmaker()
    async with sm() as session:
        yield session
```

Also: DDL execution hooks into `create_app()` — after engine creation, run `Base.metadata.create_all()`.

## 9. Data Flow Summary

```
data/raw/week_*.json
        │
        ▼  src/bilianalysis/etl/transform.py   ← library: file I/O + conversion
        │    load_raw_weeks(raw_dir)             ← sole accessor of data/
        │    transform_week(dict)                ← pure function
        │
        ▼  list[dict[str, list[dict]]]           ← full records
        │
        ▼  app/api/db/loader.py                 ← FastAPI: DB only
        │    load_incremental(session, records)  ← incremental upsert
        │    load_week(session, records)         ← per-week transaction
        │
        ▼
    PostgreSQL (6 tables)
```

## 10. Boundary Constraints

| Module | Allowed | Forbidden |
|--------|---------|-----------|
| `src/bilianalysis/etl/` | `import json`, `from pathlib import Path`, file read, dict manipulation | `import sqlalchemy`, `import asyncpg`, any DB driver |
| `app/api/db/` | `import sqlalchemy.ext.asyncio`, `import asyncpg`, DDL, DML | Reading from `data/` directory |
| `app/api/router/db_load.py` | glue: call `load_raw_weeks()` then `load_incremental()` | — |

## 11. Error Handling

| Scenario | Behavior |
|----------|----------|
| Week already in DB | Skipped, counted in `skipped` |
| Single week insert fails | Transaction rolled back for that week, recorded in `failed` dict, continue to next |
| Invalid raw data (missing field) | `PydanticEntity.model_validate()` raises, caught by `load_incremental`, week in `failed` |
| DB connection lost mid-load | Exception propagates to endpoint, returns 500. Previously-loaded weeks stay committed (they were separate transactions) |

## 12. Testing Strategy

### Unit Tests (no DB)

- `tests/test_transform.py`: verify field mapping with real `week_001.json` fixture
  - All 6 groups have correct row counts
  - UNIX timestamps → ISO datetime strings
  - creator/category dedup within a single week
  - Edge: empty videos list, missing optional fields

### Integration Tests (needs PG container)

- `tests/test_loader.py`:
  - `load_week` writes all 6 tables, row counts match
  - `load_incremental` skips already-loaded week, loads new one
  - Failed week transaction rolls back, other weeks unaffected
  - Idempotency: running twice doesn't duplicate data

## 13. Implementation Order

1. `src/bilianalysis/etl/transform.py` — pure functions, testable immediately
2. `app/api/config.py` + `app/api/deps.py` (+get_db) — configuration + session injection
3. `app/api/db/schema.py` — ORM models + Pydantic entities
4. `app/api/db/loader.py` — load_week + load_incremental
5. `app/api/router/db_load.py` — POST /api/db/load
6. Integration: register in `create_app()`, wire DDL on startup
7. Tests
