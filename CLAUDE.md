# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BiliInsight — Bilibili "每周必看" (Weekly Must-Watch) content insight platform. Crawl video data from Bilibili's weekly must-watch API, analyze with dual Pandas/PySpark engines, serve via FastAPI, visualize with Vue3 + ECharts.

**Current status**: Crawler, engines (Pandas + Spark), scheduler, config, FastAPI skeleton (crawler/analysis/tasks/config endpoints), and Vue3 frontend (home/stats/clusters/predictions 4 pages) are built. Next: PostgreSQL integration, ETL/warehouse modules, business detail endpoints, and remaining frontend pages.

Architecture design: `docs/new-scheme.md` | Original plan: `docs/README.md` | Dev docs: `docs/dev/`

## Commands

| Command                                                                  | Purpose                           |
|--------------------------------------------------------------------------|-----------------------------------|
| `uv sync`                                                                | Install all dependencies          |
| `uv add <pkg>`                                                           | Add a runtime dependency          |
| `uv add --dev <pkg>`                                                     | Add a dev dependency              |
| `uv run pytest tests/ -v`                                                | Run all 109 tests                 |
| `uv run pytest tests/test_storage.py -v`                                 | Run a single test file            |
| `uv run pytest tests/test_pipeline.py::TestRun::test_concurrent_mode -v` | Run a single test                 |
| `uv run pytest tests/ -v -k "crawl"`                                     | Run tests matching keyword        |
| `uv run python -c "..."`                                                 | Run inline Python with venv       |
| `uv run mypy .`                                                          | Run static type checking for code |
| `cd app/ui && pnpm dev`                                                  | Start frontend dev server         |
| `cd app/ui && pnpm build`                                                | Build frontend for production     |
| `cd app/ui && pnpm test:unit`                                            | Run Vitest unit tests             |
| `cd app/ui && pnpm test:e2e`                                             | Run Playwright e2e visual tests   |
| `uv run uvicorn api.app:create_app --reload`                             | Start FastAPI dev server          |

## Architecture

### Package structure

```
src/bilianalysis/          # Pure Python library — NO database drivers allowed
├── crawler/               # Data collection (complete)
│   ├── api.py             #   Bilibili API wrapper
│   ├── pipeline.py        #   Orchestration: rate limiting, retry, resume, session rotation
│   ├── storage.py         #   File I/O + progress tracking
│   └── signer.py          #   WBI signing
├── engine/                # Analysis engines (complete)
│   ├── base.py            #   ABC + 4 report models
│   ├── pandas_engine.py   #   Pandas implementation (543 lines)
│   └── spark_engine.py    #   PySpark implementation (590 lines)
├── scheduler/             # Task orchestration (complete)
│   ├── task.py / registry.py / runner.py / cron_service.py / models.py
│   └── builtins/          #   5 tasks: crawl, clean_data, statistics, clustering, prediction
├── config/                # Configuration (complete)
├── utils/                 # HTTP: fetch.py + ua.py
├── models.py              # Domain models
├── etl/                   # [planned] Data transform: raw JSON → typed records, no DB
└── warehouse/             # [planned] DWD/DWS/ADS Parquet + keywords analysis

app/                       # Application layer (partial)
├── api/                   # FastAPI — 4 router groups: crawler, analysis, tasks, config
└── ui/                    # Vue3 — 4 pages: Home, Stats, Clusters, Predictions
                           #   Vue 3.5 + Element Plus + ECharts + Alova + TailwindCSS 4
```

### Critical constraint: library vs application boundary

```
src/bilianalysis/  →  Pure Python: compute, transform, file I/O, Parquet.
                      MUST NOT import sqlalchemy, asyncpg, or any DB driver.
app/api/           →  FastAPI app. The ONLY module allowed to connect to PostgreSQL.
app/ui/            →  Vue3 frontend. Communicates with app/api/ via HTTP (Alova).
```

### Data flow

```
Bilibili API → Crawler (aiohttp) → data/raw/*.json
                                      │
                  ┌───────────────────┴───────────────────┐
                  ▼                                       ▼
    Track A: PostgreSQL (business)          Track B: Engine (analytics)
    src/bilianalysis/etl/transform.py     clean_data() → 5 Parquet tables
    (pure functions, no DB)                statistics() → StatReport JSON
           │                               clustering() → ClusterReport JSON
           ▼                               prediction() → PredictionReport JSON
    app/api/db/loader.py                         │
    (only place that executes SQL)               ▼
           │                           data/processed/*.parquet
           ▼                           data/reports/*.json
        PostgreSQL                              │
           │                                    │
           └────────────┬───────────────────────┘
                        ▼
                  FastAPI (app/api/)
                  reads PG for business queries,
                  reads report files for analytics
                        │
                        ▼
                  Vue3 (app/ui/)
```

The two tracks are independent — both source from raw JSON, neither blocks the other. Parquet = columnar analytics, PostgreSQL = row-based API queries. See `docs/new-scheme.md` §3.2 for rationale.

### Engine pipeline (4 steps)

```
create_engine(config) → PandasEngine or SparkEngine
  1. clean_data()    → CleanReport    (raw JSON → 5 Parquet tables, dedup/fill/outlier)
  2. statistics()    → StatReport     (join + groupby → overall, by_category, by_creator, by_week)
  3. clustering()    → ClusterReport  (KMeans k=3 + PCA scatter + silhouette score)
  4. prediction()    → PredictionReport (LinearRegression + 4-week forecast)
```

Engine factory at `engine/__init__.py` — `create_engine(config)` returns the right engine based on `config.analysis.engine`. Each engine writes reports to `data/reports/` after each step.

### Scheduler design

- **Task**: Abstract class with `async run(ctx: TaskContext) → TaskResult`. Registered via `@register("name")`.
- **TaskContext**: Carries `config: AppConfig` and `engine: AnalysisEngine` (lazily created). `ctx.previous` dict holds results from earlier steps.
- **PipelineRunner**: Executes a pipeline's steps sequentially. Failure mode per pipeline: `stop` (halt), `skip` (continue), or `retry` (re-attempt N times).
- **CronService**: Wraps PipelineRunner with APScheduler cron triggers. Reads schedule from config.
- **Built-in tasks**: `crawl`, `clean_data`, `statistics`, `clustering`, `prediction` — each registered at import time in `builtins/__init__.py`.

### Config system

`config.yaml` → `load_config()` → `AppConfig` Pydantic model with four sections:
- `crawler:` — request_delay, max_retries, retry_delay, cookie, key_refresh_interval, max_requests_per_session
- `analysis:` — engine (pandas | spark)
- `data:` — raw_dir, processed_dir, reports_dir
- `scheduler:` — pipelines map (name → schedule + steps + failure mode)

Global config does NOT include database settings — those belong to the FastAPI app (`app/api/config.py`).

## Key Design Decisions

- **Session-injected HTTP**: `fetch.py` does NOT own the aiohttp session — callers create and inject it. Enables connection pool sharing.
- **_jitter**: ±1s random offset on all sleep durations for anti-bot mitigation.
- **ProgressFile**: Pydantic `BaseModel` with `asyncio.Lock` for concurrent safety. Tracks `crawled`, `failed`, `last_run`.
- **Retry strategy**: New weeks get `max_retries`; previously-failed weeks get 1 retry per `run()`. -404 = permanent skip.
- **Engine abstraction**: `AnalysisEngine` ABC with 4 async/sync steps. Switch via config, not code change.
- **Parquet as analysis format**: Columnar, compressed, native to both Pandas and Spark. Not used for API point queries.
- **Library/app separation**: `src/bilianalysis/` is a pure library (no DB drivers). Only `app/api/` touches PostgreSQL. See §3.3 of `docs/new-scheme.md`.
- **Config ownership**: `config.yaml` = library + scheduler. Database URL = `app/api/` private config.
- **WBI signing**: Bilibili API requires signed parameters. `signer.py` handles key derivation and parameter signing, with auto-refresh on auth failures.

## Public API Summary

### Crawler (`from bilianalysis.crawler import`)
| Export | Kind | Description |
|--------|------|-------------|
| `CrawlRunner` | async fn | Main entry: `await CrawlRunner(config) -> CrawlReport` |
| `CrawlConfig` | Pydantic | `request_delay`, `max_retries`, `retry_delay`, `cookie`, etc. |
| `CrawlReport` | Pydantic | `total`, `crawled`, `skipped`, `failed`, `failed_weeks`, `duration_seconds` |
| `ProgressFile` | Pydantic | `crawled`, `failed`, `last_run` |
| `save_week` / `load_progress` / `save_progress` / `get_pending_weeks` | async fn | Storage helpers |
| `list_series` / `get_weekly_videos` | async fn | API calls |
| `BASE_URL` | str | Bilibili API base URL |

### Engine (`from bilianalysis.engine import`)
| Export | Kind | Description |
|--------|------|-------------|
| `create_engine(config)` | fn | Factory: returns `PandasEngine` or `SparkEngine` |
| `AnalysisEngine` | ABC | Abstract base with 4 methods |
| `PandasEngine` / `SparkEngine` | class | Concrete implementations |
| `CleanReport` / `StatReport` / `ClusterReport` / `PredictionReport` | Pydantic | Analysis output models |

### Config (`from bilianalysis.config import`)
| Export | Kind | Description |
|--------|------|-------------|
| `load_config(path?)` | fn | Load YAML → `AppConfig` |
| `AppConfig` | Pydantic | Root config with 4 sections |
| `CrawlerSection` / `AnalysisSection` / `DataSection` / `SchedulerConfig` | Pydantic | Section models |

### Scheduler (`from bilianalysis.scheduler import`)
| Export | Kind | Description |
|--------|------|-------------|
| `Task` / `TaskResult` / `TaskContext` | class | Task execution framework |
| `register` / `get_task` / `list_tasks` | fn | Task registry |
| `CronService` | class | APScheduler-backed cron runner |

## Tech Stack

- Python >= 3.13, `uv` package manager
- `aiohttp` — async HTTP; `fake-useragent` — rotating UA
- `pydantic` — config/report models, progress persistence
- `pandas` + `scikit-learn` — PandasEngine (KMeans, PCA, LinearRegression)
- `pyspark` — SparkEngine (Spark MLlib, optional HDFS via `hdfs` library)
- `pytest` + `pytest-asyncio` — 109 tests, asyncio auto mode
- `fastapi` + `uvicorn` — API server (app/api/)
- `sqlalchemy[asyncio]` + `asyncpg` — [planned] PostgreSQL integration
- Vue3 + Element Plus + ECharts + Alova + TailwindCSS 4 — frontend (app/ui/)
- `vitest` + `@playwright/test` — frontend tests
- `mypy` — static type checking

## Testing

- `asyncio_mode = "auto"` in `pyproject.toml` — no decorators needed for async tests
- Mock patterns: `unittest.mock.patch` targets module import paths (e.g., `"bilianalysis.crawler.api.get"`)
- File I/O tests use `tmp_path` + `monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)`
- Module-level test constants (`SERIES_LIST`, `WEEKLY_DATA`) shared across test classes
- Engine tests verify all 4 analysis steps produce valid report models
- Scheduler tests mock individual tasks and verify pipeline failure modes (stop/skip/retry)
- After test or before the end, uses `mypy` tool to check code about static type