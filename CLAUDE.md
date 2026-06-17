# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bilibili "每周必看" (Weekly Must-Watch) data analysis platform. Crawl video data from Bilibili's weekly must-watch API, then analyze with Pandas and PySpark. Currently in early setup phase — only the async HTTP fetch utility exists.

Full project plan and technical architecture: `docs/README.md`

## Commands

- **Package manager**: `uv` — use `uv add`, `uv sync`, `uv run` for all package operations
- **Run main script**: `uv run python main.py` (currently a PyCharm placeholder; will be replaced by the crawler entry point)

## Architecture

### Current (implemented)

```
src/
├── crawler/          # Bilibili API crawling logic (empty, to be built)
└── utils/
    ├── fetch.py      # Async HTTP GET with aiohttp + fake_useragent
    └── ua.py         # Singleton fake_useragent.UserAgent instance
```

- `src/utils/ua.py` — provides a shared `ua` (UserAgent) instance imported by `fetch.py`
- `src/utils/fetch.py` — `get(url, headers, timeout)` performs an async GET, injects a random User-Agent, parses JSON. Timeout defaults: connect 3s, total 10s. Returns parsed JSON or `None` on failure.

### Planned (from `docs/README.md`)

**Data pipeline**: Raw JSON (`data/raw/`) → cleaned Parquet (`data/processed/`) → analysis reports (`data/reports/`)

**Dual analysis engine** with a common abstract interface (`AnalysisEngine`):
| Engine | Library | Use case |
|--------|---------|----------|
| `PandasEngine` | Pandas, Scikit-Learn | Small/medium data, dev workstation |
| `SparkEngine` | PySpark, Spark MLlib | Large-scale distributed processing |

Engine selection via YAML config (`analysis.engine: pandas|spark`), loaded at startup.

**Backend**: FastAPI + Uvicorn + Pydantic (REST API serving analysis results)

**Frontend** (planned): Vue3 + TypeScript + Element Plus + ECharts5 (dashboard with partition analysis, UP主 rankings, trend charts, clustering viz)

**Analysis modules** (each implemented for both engines):
- Video statistics (counts, averages, interaction rates)
- Category/partition popularity analysis
- UP主 frequency and influence rankings (TOP10)
- Weekly time-series trends (views, likes, interaction rates)
- KMeans clustering (features: view, like, coin, favorite → 3 tiers: viral, popular, rising)
- Linear regression for view/like trend prediction

## Tech Stack

- Python >= 3.13
- `aiohttp` — async HTTP for the crawler
- `fake-useragent` — rotating User-Agent headers
- Pandas + Scikit-Learn (planned)
- PySpark + Spark MLlib (planned)
- FastAPI + Uvicorn (planned)
- Vue3 + TypeScript + Element Plus + ECharts5 (planned)

## Directory Purposes

| Directory | Purpose |
|-----------|---------|
| `src/crawler/` | Bilibili API crawler (to be built) |
| `src/utils/` | Shared utilities (HTTP, UA, etc.) |
| `app/` | Application code — both FastAPI backend and Vue3 frontend (to be built) |
| `data/` | Raw, processed, and report data files |
| `docs/` | Project documentation and plans |
| `docs/dev/` | Development notes and logs |
| `tests/` | Test suite (empty, to be populated) |
