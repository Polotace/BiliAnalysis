# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bilibili "每周必看" (Weekly Must-Watch) data analysis platform. Crawl video data from Bilibili's weekly must-watch API, then analyze with Pandas and PySpark.

**Current status**: Data collection (crawler) module complete. Analysis engines, FastAPI backend, and Vue3 frontend are planned but not yet built.

Full project plan: `docs/README.md` | Dev docs: `docs/dev/` | Test docs: `docs/test/`

## Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install all dependencies |
| `uv add <pkg>` | Add a runtime dependency |
| `uv add --dev <pkg>` | Add a dev dependency |
| `uv run pytest tests/ -v` | Run all 36 tests |
| `uv run pytest tests/test_storage.py -v` | Run a single test file |
| `uv run pytest tests/test_pipeline.py::TestRun::test_concurrent_mode -v` | Run a single test |
| `uv run python -c "..."` | Run inline Python with venv |

## Architecture

### Package structure

```
src/bilianalysis/
├── __init__.py              # empty
├── utils/
│   ├── fetch.py             # async HTTP client (aiohttp, session-injected)
│   └── ua.py                # shared fake_useragent.UserAgent instance
└── crawler/
    ├── api.py               # Bilibili "每周必看" API wrapper (2 endpoints)
    ├── storage.py           # file I/O + progress tracking (Pydantic model)
    └── pipeline.py          # orchestration: rate limiting, retry, resume, concurrent
data/raw/                    # runtime data (week_001.json, progress.json)
tests/                       # pytest-asyncio test suite
```

### Data flow

```
create_session() → api.list_series() → storage.get_pending_weeks()
    → for each pending week: api.get_weekly_videos()
        → storage.save_week() → storage.save_progress()
    → return CrawlReport
```

### Key design decisions

- **Session-injected**: `fetch.py` does NOT own the aiohttp session — callers (`pipeline.py`) create and inject it. This lets sequential and concurrent modes share one connection pool.
- **_jitter**: ±1s random offset on all sleep durations to avoid bot detection.
- **ProgressFile**: Pydantic `BaseModel`, not dict. Fields: `crawled` (list[int]), `failed` (dict[int, str]), `last_run` (datetime | None). Protected by `asyncio.Lock`.
- **Retry strategy**: New weeks get `max_retries` attempts; previously-failed weeks get exactly 1 retry per `run()` call. Failures are recorded and summarized in `CrawlReport`.
- **Pydantic models**: `CrawlConfig` (config), `CrawlReport` (output), `ProgressFile` (persistence).

### Public API (via `from bilianalysis.crawler import`)

| Export | Kind | Description |
|--------|------|-------------|
| `CrawlRunner` | `async fn` | Main entry: `await CrawlRunner(config) -> CrawlReport` |
| `CrawlConfig` | Pydantic model | `mode`, `concurrency`, `request_delay`, `max_retries`, `retry_delay` |
| `CrawlReport` | Pydantic model | `total`, `crawled`, `skipped`, `failed`, `failed_weeks`, `duration_seconds` |
| `ProgressFile` | Pydantic model | `crawled`, `failed`, `last_run` |
| `save_week` | `async fn` | Persist one week's data |
| `load_progress` / `save_progress` | `async fn` | Read/write progress file |
| `get_pending_weeks` | `async fn` | Compute (retry, pending) week lists |
| `list_series` / `get_weekly_videos` | `async fn` | Bilibili API calls |
| `BASE_URL` | `str` | Bilibili API base URL |

## Tech Stack

- Python >= 3.13, `uv` package manager
- `aiohttp` — async HTTP; `fake-useragent` — rotating UA
- `pydantic` — config/report models, progress persistence
- `pytest` + `pytest-asyncio` — test suite (36 tests, asyncio auto mode)

## Testing

- `asyncio_mode = "auto"` in `pyproject.toml` — no need to decorate async tests
- Mock patterns: `unittest.mock.patch` targets module import paths (e.g., `"bilianalysis.crawler.api.get"`)
- File I/O tests use `tmp_path` + `monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)`
- Module-level test constants (`SERIES_LIST`, `WEEKLY_DATA`) shared across test classes
