# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BiliInsight — Bilibili "每周必看" content insight platform. Crawl video data from Bilibili API, analyze with Pandas engine, serve via FastAPI + PostgreSQL, visualize with Vue3 + ECharts + Element Plus.

**Current status**: Crawler (anti-bot hardened), Pandas engine (4-step pipeline), warehouse (DWD/DWS/ADS), scheduler (7 registered tasks), FastAPI (10 router groups), PostgreSQL integration (schema + loader + business queries), Vue3 frontend (12 pages + 26 components), admin backend page. Content analysis (jieba NLP + word cloud) is the next phase.

## Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install all Python dependencies |
| `uv add <pkg>` | Add a runtime dependency |
| `uv run pytest tests/ -v` | Run all 143 backend tests |
| `uv run pytest tests/test_engine.py -v` | Run a single test file |
| `uv run pytest tests/ -v -k "crawl"` | Run tests matching keyword |
| `uv run bilianalysis serve --port 8080` | Start FastAPI dev server |
| `cd app/ui && pnpm dev` | Start frontend dev server (port 5173, proxies /api → 8080) |
| `cd app/ui && pnpm build` | Build frontend for production |
| `cd app/ui && pnpm test:unit` | Run Vitest unit tests (14 tests) |
| `cd app/ui && pnpm test:e2e` | Run Playwright e2e tests |

## Architecture

### Critical constraint: library vs application boundary

```
src/bilianalysis/  →  Pure Python library — compute, transform, file I/O, Parquet.
                      MUST NOT import sqlalchemy, asyncpg, or any DB driver.
                      MUST NOT import from app/.
app/api/           →  FastAPI app. The ONLY module allowed to connect to PostgreSQL.
app/api/tasks/     →  Scheduler tasks that need DB access (e.g. db_load).
                      Registered via @register just like library tasks.
app/cli/           →  Typer CLI (serve + schedule subcommands).
app/ui/            →  Vue3 frontend. Communicates with app/api/ via HTTP (Alova).
```

### Package structure

```
src/bilianalysis/
├── crawler/          # Bilibili API + anti-bot pipeline
│   ├── api.py        #   list_series, get_weekly_videos, get_creator_relation_stats
│   ├── pipeline.py   #   Sequential crawl: rate limiting, retry, WBI key refresh,
│   │                 #   session rotation, device fingerprint, exponential backoff
│   ├── storage.py    #   ProgressFile (Pydantic + asyncio.Lock)
│   └── signer.py     #   WBI signing (w_rid, wts, web_location variants)
├── engine/           # PandasEngine: clean_data → statistics → clustering → prediction
├── warehouse/        # DWD (fact) → DWS (creator/category/weekly aggregates) → ADS (4 tables)
├── scheduler/        # @register decorator, PipelineRunner, CronService
│   └── builtins/     # 6 library tasks: crawl, clean_data, statistics, clustering,
│                     #   prediction, build_warehouse
├── config/           # YAML + env var → AppConfig Pydantic
├── utils/            # fetch.py (aiohttp + device fingerprint), ua.py (fake-useragent)
├── etl/              # transform_week(): raw JSON → typed records (pure, no DB)
└── nlp/              # [planned] jieba keyword extraction
```

### Data flow

```
Bilibili API → Crawler → data/raw/*.json
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
Track A: PostgreSQL (business queries)     Track B: Engine (analytics)
  transform_week() → loader.py → PG         clean_data() → 5 Parquet tables
  API reads PG via queries.py               statistics/clustering/prediction → JSON reports
          │                                       │
          └──────────────┬────────────────────────┘
                         ▼
                   FastAPI (10 router groups)
                         │
                         ▼
                   Vue3 (12 pages)
```

### Frontend pages (12)

| Route | Page | Section |
|-------|------|---------|
| `/` | HomePage | 发现 |
| `/videos` | VideoLibraryPage | 浏览 |
| `/videos/:aid` | VideoDetailPage | 浏览 |
| `/weeks` | WeeksPage | 浏览 |
| `/weeks/:number` | WeekDetailPage | 浏览 |
| `/creators` | CreatorsPage | 浏览 |
| `/creators/:mid` | CreatorDetailPage | 浏览 |
| `/categories` | CategoriesPage | 浏览 |
| `/analysis/stats` | StatsPage | 分析 |
| `/analysis/clusters` | ClusterPage | 分析 |
| `/analysis/predictions` | PredictPage | 分析 |
| `/admin` | AdminPage | 管理 |

Navigation: TopNav has 发现 | 分析 | 浏览 (dropdown on mobile, Sidebar on desktop).
Sidebar auto-switches between browse and analysis sub-nav based on route.
Keep-alive caches HomePage, VideoLibraryPage, WeeksPage, CreatorsPage.

### Scheduler tasks (7 registered)

`crawl`, `clean_data`, `statistics`, `clustering`, `prediction`, `build_warehouse`, `db_load`

`db_load` lives in `app/api/tasks/` (needs PostgreSQL). Library tasks auto-register via
`import bilianalysis.scheduler.builtins`; app tasks via `import app.api.tasks`.

### Config system

`config.yaml` → `load_config()` → `AppConfig` with four sections: `crawler`, `analysis`, `data`, `scheduler`.
Database URL lives in `app/api/config.py` (pydantic-settings, `.env` file), not in global config.
Pipeline steps are registered task names; failure mode per pipeline: `stop` / `skip` / `retry`.

### Anti-crawl measures

- Device fingerprint cookies: buvid3/4, b_lsid via `make_device_cookie()`
- Header rotation: Referer (4 variants), Accept-Language (3 variants), User-Agent
- WBI signing with ms-precision wts, web_location variants, proactive key refresh
- Global shared rate-limit state with exponential backoff (×2 on -352, ×3 on 412)
- Session rotation on consecutive -352 hits (new device ID)
- Image proxy endpoint (`/api/proxy/image`) for Bilibili CDN covers (Referer required)

## Key Design Decisions

- **Library/app boundary**: `src/bilianalysis/` is pure Python. Only `app/api/` touches PostgreSQL.
- **Session-injected HTTP**: `fetch.py` does NOT own the aiohttp session — callers create/inject it.
- **Task registry**: `@register("name")` decorator. Library tasks in `builtins/`, DB tasks in `app/api/tasks/`.
- **Keep-alive**: Browse list pages cached in `<keep-alive>` so scroll/filter state survives navigation.
- **Infinite scroll**: Uses Element Plus `el-scrollbar` + `@end-reached` event (not pagination buttons).
- **Execution history**: Persisted to `data/run_history.csv` via `app/api/history.py`. Survives restarts.
- **Scalar types**: All Bilibili ID columns (mid, cid, aid, tid) must be PostgreSQL `BIGINT`, not `INTEGER`.
- **WBI field names**: Bilibili API uses `stime`/`etime`, not `start_time`/`end_time`.

## Testing

- `asyncio_mode = "auto"` — no decorators needed for async tests
- Mock patterns: `unittest.mock.patch` targets module import paths (e.g., `"bilianalysis.crawler.pipeline.list_series"`)
- File I/O tests use `tmp_path` + `monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)`
- Engine tests verify all 4 analysis steps produce valid Pydantic report models
- Scheduler tests mock individual tasks and verify failure modes (stop/skip/retry)
- 143 Python tests + 14 Vitest frontend tests + Playwright e2e scaffold
