# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BiliInsight — Bilibili "每周必看" content insight platform. Crawl video data from Bilibili API, analyze with Pandas engine, serve via FastAPI + PostgreSQL, visualize with Vue3 + ECharts + Element Plus.

**Current status**: Crawler (anti-bot hardened), Pandas engine (5-step pipeline including model_comparison with NLP + Bayesian opt), warehouse (DWD/DWS/ADS), scheduler (8 registered tasks), FastAPI (10 router groups), PostgreSQL integration, Vue3 frontend (13 pages), admin backend with API Key auth.

## Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install all Python dependencies |
| `uv run pytest tests/ -v` | Run all 146 backend tests |
| `uv run pytest tests/test_engine.py -v` | Run a single test file |
| `uv run pytest tests/ -v -k "crawl"` | Run tests matching keyword |
| `uv run bilianalysis serve --port 8080` | Start FastAPI dev server (auto-generates admin key if not configured) |
| `cd app/ui && pnpm dev` | Start frontend dev server (port 5173, proxies /api → 8080) |
| `cd app/ui && pnpm build` | Build frontend for production |
| `cd app/ui && pnpm test:unit` | Run Vitest unit tests |
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

### Engine pipeline (5 steps)

```
clean_data → statistics → clustering → prediction → model_comparison
```

- **clean_data**: Raw JSON → 5 Parquet tables (Weekly/Video/Creator/Category/VideoStat)
- **statistics**: Parquet → join → groupby → StatReport (overall / by_category / by_creator / by_week)
- **clustering**: KMeans(k=3) on (view, like, coin, favorite) → PCA(2D) scatter
- **prediction**: Week-level LinearRegression (avg_view ~ week_number + video_count). Time-series forecast, NOT video-level.
- **model_comparison**: Video-level 7-model regression (6 baselines + Bayesian-optimized XGBoost). Loads raw JSON directly (needs extended fields like dynamic/rcmd_reason/width/height not in Parquet). 5-fold CV with 172 features (127 metadata + 45 NLP jieba TF-IDF keywords). Reuses `clean_title()` and STOPWORDS from `bilianalysis.nlp.keywords`. XGBoost + LightGBM + scikit-optimize are optional (ImportError fallback).

### NLP module

`src/bilianalysis/nlp/` — jieba TF-IDF keyword extraction from video titles. Provides `clean_title()`, `STOPWORDS`, `extract_keywords()`. Used both by the keywords analysis page and by engine's model_comparison for NLP binary features.

### Scheduler tasks (8 registered)

`crawl`, `clean_data`, `statistics`, `clustering`, `prediction`, `build_warehouse`, `db_load`, `keywords`, `model_comparison`

`db_load` lives in `app/api/tasks/` (needs PostgreSQL). Library tasks in `builtins/` auto-register via import. `model_comparison` task generates `model_comparison_report.json` which the API serves from cache.

### Config system

`config.yaml` → `load_config()` → `AppConfig` with four sections: `crawler`, `analysis`, `data`, `scheduler`.
Database URL and `admin_api_key` live in `app/api/config.py` (pydantic-settings, `.env`), not in global config.

### Admin auth

API Key authentication via `X-API-Key` header. `deps.py:require_admin()` validates against `app.state.api_settings.admin_api_key`. Auto-generated on startup if not configured in `.env`/environment. Protects 6 write endpoints (`POST /crawler`, `/analysis`, `/tasks/{name}/run`, `/task/{name}`, `/db/load`, `PUT /config`). Frontend `useApi.ts` auto-injects key from `localStorage` on non-GET requests. AdminPage provides key input UI.

### Frontend pages (13)

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
| `/analysis/keywords` | KeywordsPage | 分析 |
| `/analysis/models` | ModelComparisonPage | 分析 |
| `/admin` | AdminPage | 管理 |

### Frontend component conventions

- **PageShell** — content wrapper (`max-w-7xl mx-auto`). Accepts `sidebar` prop for `lg:ml-44` sidebar offset (pages with Sidebar use `<PageShell sidebar>`).
- **Sidebar** — fixed left sidebar (176px), hidden below `lg:`, context-switches between browse/analysis links based on route.
- **AnalysisLoading** — reusable loading animation (scanner-line metaphor) used by all 5 analysis pages instead of `animate-pulse` skeletons.
- **StatCard / SectionHeader** — shared presentation components.
- **ECharts** — registered via `useChart.ts` (LineChart, BarChart, ScatterChart). Chart components receive `EChartsOption` objects, not raw config.

### Keep-alive and layout

- `App.vue` caches HomePage, VideoLibraryPage, WeeksPage, CreatorsPage in `<keep-alive>`.
- Infinite scroll pages use Element Plus `el-scrollbar` + `@end-reached` event.
- Mobile: Sidebar hidden, SubNavTabs shown. Desktop: Sidebar visible, SubNavTabs hidden.

## Key Design Decisions

- **Library/app boundary**: `src/bilianalysis/` is pure Python. Only `app/api/` touches PostgreSQL.
- **Session-injected HTTP**: `fetch.py` does NOT own the aiohttp session — callers create/inject it.
- **Task registry**: `@register("name")` decorator. Library tasks in `builtins/`, DB tasks in `app/api/tasks/`.
- **API cache-first pattern**: Analysis endpoints check for cached report JSON first, fall back to live engine computation.
- **Scalar types**: All Bilibili ID columns (mid, cid, aid, tid) must be PostgreSQL `BIGINT`, not `INTEGER`.
- **WBI field names**: Bilibili API uses `stime`/`etime`, not `start_time`/`end_time`.
- **Execution history**: Persisted to `data/run_history.csv` via `app/api/history.py`.
- **AnalysisOverview**: Includes all 6 report types (clean, stats, cluster, prediction, keywords, model_comparison).

## Testing

- `asyncio_mode = "auto"` — no decorators needed for async tests
- Mock patterns: `unittest.mock.patch` targets module import paths (e.g., `"bilianalysis.crawler.pipeline.list_series"`)
- File I/O tests use `tmp_path` + `monkeypatch.setattr`
- API tests use `TestClient`; `auth_client` fixture for authenticated write tests (auto-injects `X-API-Key` matching `app.state.api_settings.admin_api_key`)
- Engine tests verify Pydantic report models
- Scheduler tests mock individual tasks and verify failure modes (stop/skip/retry)
- 146 Python tests
