# Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build FastAPI backend exposing crawler, analysis, tasks, and config management via REST API under `app/api/`.

**Architecture:** `app/api/app.py` creates FastAPI app with CORS + error handlers. 4 router modules in `app/api/router/` handle endpoints. `deps.py` provides FastAPI dependency injection for config/runner/engine. Schemas and errors are defined in standalone modules. CLI serve command in `app/cli/serve_cmd.py`.

**Tech Stack:** fastapi, uvicorn, pydantic (existing)

---

## File Structure

```
Create:
├── app/api/__init__.py              # exports create_app
├── app/api/app.py                   # create_app() factory
├── app/api/deps.py                  # get_config, get_runner, get_engine
├── app/api/schemas.py               # API request/response models
├── app/api/errors.py                # AppError hierarchy
├── app/api/router/__init__.py
├── app/api/router/crawler.py        # /api/crawler
├── app/api/router/analysis.py       # /api/analysis + sub-routes
├── app/api/router/tasks.py          # /api/tasks
├── app/api/router/config.py         # /api/config
├── app/cli/serve_cmd.py             # bilianalysis serve subcommand

Modify:
├── app/cli/__init__.py              # register serve subcommand
├── pyproject.toml                   # deps + [project.scripts]
```

---

### Task 1: Add deps + create skeleton (errors, schemas, router package)

**Files:**
- Modify: `pyproject.toml`
- Create: `app/api/__init__.py`
- Create: `app/api/errors.py`
- Create: `app/api/schemas.py`
- Create: `app/api/router/__init__.py`

- [ ] **Step 1: Add fastapi + uvicorn**

Run:
```bash
uv add fastapi uvicorn
```

- [ ] **Step 2: Verify imports**

Run: `uv run python -c "import fastapi, uvicorn; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Create errors.py**

Create `app/api/errors.py`:
```python
"""Business exceptions for API layer."""


class AppError(Exception):
    """Base error with HTTP status code."""
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail


class TaskNotFound(AppError):
    def __init__(self, name: str):
        super().__init__(404, f"Task '{name}' not found")


class PipelineNotFound(AppError):
    def __init__(self, name: str):
        super().__init__(404, f"Pipeline '{name}' not found")


class ConfigInvalid(AppError):
    def __init__(self, msg: str):
        super().__init__(400, f"Invalid config: {msg}")


class EngineUnavailable(AppError):
    def __init__(self):
        super().__init__(503, "Analysis engine not available")
```

- [ ] **Step 4: Create schemas.py**

Create `app/api/schemas.py`:
```python
"""API request/response models. Engine reports reused from bilianalysis.engine.base."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from bilianalysis.engine.base import (
    CleanReport, StatReport, ClusterReport, PredictionReport,
)


# ── Generic ──

class TaskTriggerResponse(BaseModel):
    run_id: str
    pipeline: str
    status: str = "accepted"


# ── Crawler ──

class CrawlerStatus(BaseModel):
    total_weeks: int
    crawled: int
    failed: dict[int, str]
    last_run: datetime | None
    is_running: bool = False


# ── Analysis ──

class AnalysisOverview(BaseModel):
    last_clean: CleanReport | None = None
    last_stats: StatReport | None = None
    last_cluster: ClusterReport | None = None
    last_prediction: PredictionReport | None = None


# ── Tasks ──

class PipelineInfo(BaseModel):
    name: str
    schedule: str
    steps: list[str]
    step_failure: str


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineInfo]


class RunHistoryItem(BaseModel):
    run_id: str
    pipeline: str
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    step_count: int
    failed_step: str | None = None


# ── Config ──

class ConfigUpdateRequest(BaseModel):
    section: Literal["crawler", "analysis", "data", "scheduler"]
    values: dict
    persist: bool = False
```

- [ ] **Step 5: Create router/__init__.py + api/__init__.py**

Create `app/api/__init__.py`:
```python
from app.api.app import create_app

__all__ = ["create_app"]
```

Create `app/api/router/__init__.py`:
```python
"""API route modules."""
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/api/
git commit -m "feat: add API skeleton (errors, schemas, router package)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Dependency injection

**Files:**
- Create: `app/api/deps.py`

- [ ] **Step 1: Create deps.py**

Create `app/api/deps.py`:
```python
"""FastAPI dependency injection for config, runner, and engine."""
from typing import Annotated

from fastapi import Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.runner import PipelineRunner


def get_config(request: Request) -> AppConfig:
    """Get the runtime AppConfig stored on app.state."""
    return request.app.state.config


def get_runner(
    config: Annotated[AppConfig, Depends(get_config)],
) -> PipelineRunner:
    """Create a PipelineRunner from the current config."""
    return PipelineRunner(config)


def get_engine(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AnalysisEngine:
    """Create an AnalysisEngine from the current config.

    Uses the create_engine() factory to pick Pandas or Spark.
    """
    from bilianalysis.engine import create_engine
    return create_engine(config)
```

- [ ] **Step 2: Verify imports**

Run: `uv run python -c "from app.api.deps import get_config, get_runner, get_engine; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add API dependency injection (config, runner, engine)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: App factory with error handlers + CORS

**Files:**
- Create: `app/api/app.py`

- [ ] **Step 1: Create app.py**

Create `app/api/app.py`:
```python
"""FastAPI application factory."""
import logging
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from app.api.errors import AppError

logger = logging.getLogger("bilianalysis.api")


def create_app(config: AppConfig) -> FastAPI:
    """Create a configured FastAPI application.

    Args:
        config: The application configuration.

    Returns:
        A FastAPI app ready for uvicorn.run().
    """
    app = FastAPI(title="BiliAnalysis API", version="0.1.0")

    # Runtime shared state
    app.state.config = config
    app.state.run_history: deque[RunRecord] = deque(maxlen=200)

    # CORS (frontend dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from app.api.router import crawler, analysis, tasks, config as config_router
    app.include_router(crawler.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(config_router.router, prefix="/api")

    # Register error handlers
    _register_error_handlers(app)

    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
```

- [ ] **Step 2: Verify factory works (no routes yet, just app creation)**

Run: `uv run python -c "
from bilianalysis.config.model import AppConfig
from app.api import create_app
app = create_app(AppConfig())
print(f'App: {app.title} v{app.version}')
print('OK')
"`
Expected: `App: BiliAnalysis API v0.1.0` followed by `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/app.py app/api/__init__.py
git commit -m "feat: add API app factory with CORS and error handlers

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: router/crawler.py

**Files:**
- Create: `app/api/router/crawler.py`

- [ ] **Step 1: Create crawler.py**

Create `app/api/router/crawler.py`:
```python
"""Crawler endpoints: /api/crawler"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.crawler import CrawlRunner
from bilianalysis.crawler.storage import load_progress
from bilianalysis.scheduler.models import RunRecord
from app.api.deps import get_config
from app.api.schemas import TaskTriggerResponse, CrawlerStatus

router = APIRouter(tags=["crawler"])


@router.post("/crawler", status_code=202, response_model=TaskTriggerResponse)
async def trigger_crawl(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
):
    """Trigger a crawl task in the background."""
    record = RunRecord(
        pipeline="crawler", trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            await CrawlRunner(config.crawler)
            record.status = "success"
        except Exception as exc:
            record.status = "failed"
            record.step_results = [{
                "task_name": "crawl", "status": "failed",
                "duration_seconds": 0, "error": str(exc),
            }]
        finally:
            record.finished_at = datetime.now(timezone.utc)

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline="crawler")


@router.get("/crawler", response_model=CrawlerStatus)
async def get_crawler_status(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
):
    """Get crawler progress from progress.json and run history."""
    progress = await load_progress()
    # Check if a crawl is currently running
    is_running = any(
        r.pipeline == "crawler" and r.status == "running"
        for r in request.app.state.run_history
    )
    return CrawlerStatus(
        total_weeks=len(progress.crawled) + len(progress.failed),
        crawled=len(progress.crawled),
        failed={int(k): v for k, v in progress.failed.items()},
        last_run=progress.last_run,
        is_running=is_running,
    )
```

- [ ] **Step 2: Verify route registers (no 404)**

Run: `uv run python -c "
from bilianalysis.config.model import AppConfig
from fastapi.testclient import TestClient
from app.api import create_app

app = create_app(AppConfig())
client = TestClient(app)
# Test health-like check: GET /api/crawler (may error on missing data, but should be 200 or 4xx, not 404)
resp = client.get('/api/crawler')
assert resp.status_code != 404, f'Route not found: {resp.status_code}'
print('OK: route registered')
"`

- [ ] **Step 3: Commit**

```bash
git add app/api/router/crawler.py
git commit -m "feat: add crawler API endpoints (POST/GET /api/crawler)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: router/analysis.py

**Files:**
- Create: `app/api/router/analysis.py`

- [ ] **Step 1: Create analysis.py**

Create `app/api/router/analysis.py`:
```python
"""Analysis endpoints: /api/analysis and sub-routes."""
import asyncio
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import (
    AnalysisEngine, StatReport, ClusterReport, PredictionReport,
)
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from app.api.deps import get_config, get_runner, get_engine
from app.api.errors import EngineUnavailable
from app.api.schemas import TaskTriggerResponse, AnalysisOverview

router = APIRouter(tags=["analysis"])


def _reports_dir(config: AppConfig) -> Path:
    return Path(config.data.reports_dir)


def _read_json(path: Path) -> dict | None:
    """Read a JSON file if it exists, return None otherwise."""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


@router.post("/analysis", status_code=202, response_model=TaskTriggerResponse)
async def trigger_analysis(
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[PipelineRunner, Depends(get_runner)],
    request: Request,
):
    """Trigger a full analysis pipeline (clean -> stats -> cluster -> predict)."""
    record = RunRecord(
        pipeline="analysis", trigger="manual",
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            # Import builtins to register analysis tasks
            import bilianalysis.scheduler.builtins  # noqa: F401
            result = await runner.run("analysis", trigger="manual")
            record.status = result.status
            record.step_results = result.step_results
        except Exception as exc:
            record.status = "failed"
            record.step_results = [{
                "task_name": "analysis", "status": "failed",
                "duration_seconds": 0, "error": str(exc),
            }]
        finally:
            record.finished_at = record.finished_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline="analysis")


@router.get("/analysis", response_model=AnalysisOverview)
async def get_analysis_overview(config: Annotated[AppConfig, Depends(get_config)]):
    """Return an overview of the latest analysis results from reports/."""
    rd = _reports_dir(config)
    return AnalysisOverview(
        last_clean=_read_json(rd / "clean_report.json"),
        last_stats=_read_json(rd / "stats_report.json"),
        last_cluster=_read_json(rd / "cluster_report.json"),
        last_prediction=_read_json(rd / "prediction_report.json"),
    )


@router.get("/analysis/stats", response_model=StatReport)
async def get_stats(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get statistics report. Reads from reports/ if available, falls back to engine."""
    cached = _read_json(_reports_dir(config) / "stats_report.json")
    if cached:
        return StatReport(**cached)
    return engine.statistics()


@router.get("/analysis/clusters", response_model=ClusterReport)
async def get_clusters(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get clustering report."""
    cached = _read_json(_reports_dir(config) / "cluster_report.json")
    if cached:
        return ClusterReport(**cached)
    return engine.clustering()


@router.get("/analysis/predictions", response_model=PredictionReport)
async def get_predictions(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get prediction report."""
    cached = _read_json(_reports_dir(config) / "prediction_report.json")
    if cached:
        return PredictionReport(**cached)
    return engine.prediction()
```

- [ ] **Step 2: Verify route registration**

Run: `uv run python -c "
from bilianalysis.config.model import AppConfig
from fastapi.testclient import TestClient
from app.api import create_app

app = create_app(AppConfig())
client = TestClient(app)
for path in ['/api/analysis', '/api/analysis/stats', '/api/analysis/clusters', '/api/analysis/predictions']:
    resp = client.get(path)
    assert resp.status_code != 404, f'{path} returned 404'
print('All analysis routes OK')
"`

- [ ] **Step 3: Commit**

```bash
git add app/api/router/analysis.py
git commit -m "feat: add analysis API endpoints (POST/GET /api/analysis + sub-routes)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: router/tasks.py

**Files:**
- Create: `app/api/router/tasks.py`

- [ ] **Step 1: Create tasks.py**

Create `app/api/router/tasks.py`:
```python
"""Task/pipeline endpoints: /api/tasks"""
import asyncio
from typing import Annotated

from fastapi import APIRouter, Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from app.api.deps import get_config, get_runner
from app.api.errors import PipelineNotFound
from app.api.schemas import (
    TaskTriggerResponse, PipelineInfo, PipelineListResponse, RunHistoryItem,
)

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=PipelineListResponse)
async def list_pipelines(config: Annotated[AppConfig, Depends(get_config)]):
    """List all configured pipelines."""
    pipelines = [
        PipelineInfo(
            name=name,
            schedule=pl.schedule,
            steps=pl.steps,
            step_failure=pl.step_failure,
        )
        for name, pl in config.scheduler.pipelines.items()
    ]
    return PipelineListResponse(pipelines=pipelines)


@router.post("/tasks/{name}/run", status_code=202, response_model=TaskTriggerResponse)
async def trigger_pipeline(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[PipelineRunner, Depends(get_runner)],
    request: Request,
):
    """Trigger a named pipeline in the background."""
    if name not in config.scheduler.pipelines:
        raise PipelineNotFound(name)

    record = RunRecord(pipeline=name, trigger="manual")
    request.app.state.run_history.append(record)

    async def _run():
        try:
            import bilianalysis.scheduler.builtins  # noqa: F401
            result = await runner.run(name, trigger="manual")
            record.status = result.status
            record.step_results = result.step_results
        except Exception as exc:
            record.status = "failed"
            record.step_results = [{
                "task_name": name, "status": "failed",
                "duration_seconds": 0, "error": str(exc),
            }]
        finally:
            from datetime import datetime, timezone
            record.finished_at = datetime.now(timezone.utc)

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline=name)


@router.get("/tasks/{name}/history", response_model=list[RunHistoryItem])
async def pipeline_history(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    limit: int = 50,
):
    """Get execution history for a pipeline."""
    if name not in config.scheduler.pipelines:
        raise PipelineNotFound(name)

    runs = [r for r in request.app.state.run_history if r.pipeline == name]
    items = []
    for r in runs[-limit:]:
        failed_step = None
        for sr in r.step_results:
            if sr.status == "failed":
                failed_step = sr.task_name
                break
        items.append(RunHistoryItem(
            run_id=r.run_id,
            pipeline=r.pipeline,
            trigger=r.trigger,
            started_at=r.started_at,
            finished_at=r.finished_at,
            status=r.status,
            step_count=len(r.step_results),
            failed_step=failed_step,
        ))
    return items
```

- [ ] **Step 2: Verify route registration**

Run: `uv run python -c "
from bilianalysis.config.model import AppConfig
from fastapi.testclient import TestClient
from app.api import create_app

app = create_app(AppConfig())
client = TestClient(app)
resp = client.get('/api/tasks')
assert resp.status_code == 200, f'GET /api/tasks returned {resp.status_code}'
data = resp.json()
assert 'pipelines' in data
print(f'OK: {len(data[\"pipelines\"])} pipelines')
"`

- [ ] **Step 3: Commit**

```bash
git add app/api/router/tasks.py
git commit -m "feat: add tasks API endpoints (GET/POST /api/tasks + history)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: router/config.py

**Files:**
- Create: `app/api/router/config.py`

- [ ] **Step 1: Create config.py**

Create `app/api/router/config.py`:
```python
"""Config endpoints: /api/config"""
import yaml
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException

from bilianalysis.config.model import AppConfig
from app.api.deps import get_config
from app.api.schemas import ConfigUpdateRequest

router = APIRouter(tags=["config"])


def _config_to_dict(config: AppConfig) -> dict:
    """Serialize AppConfig to a JSON-safe dict."""
    return {
        "crawler": config.crawler.model_dump(),
        "analysis": config.analysis.model_dump(),
        "data": config.data.model_dump(),
        "scheduler": config.scheduler.model_dump(),
    }


@router.get("/config")
async def get_config_endpoint(config: Annotated[AppConfig, Depends(get_config)]):
    """Return the current effective configuration."""
    return _config_to_dict(config)


@router.put("/config")
async def update_config(
    body: ConfigUpdateRequest,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
):
    """Update runtime configuration, optionally persisting to config.yaml."""
    section_attr = body.section
    if not hasattr(config, section_attr):
        raise HTTPException(400, f"Unknown config section: {body.section}")

    target = getattr(config, section_attr)
    try:
        for key, value in body.values.items():
            if hasattr(target, key):
                setattr(target, key, value)
            else:
                raise HTTPException(
                    400, f"Unknown field '{key}' in section '{body.section}'"
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Failed to update config: {exc}")

    # Persist to YAML if requested
    if body.persist:
        try:
            config_path = "config.yaml"
            full_config = _config_to_dict(config)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(full_config, f, allow_unicode=True, default_flow_style=False)
        except Exception as exc:
            raise HTTPException(500, f"Failed to write config.yaml: {exc}")

    return {"detail": f"Section '{body.section}' updated", "persisted": body.persist}
```

- [ ] **Step 2: Verify route**

Run: `uv run python -c "
from bilianalysis.config.model import AppConfig
from fastapi.testclient import TestClient
from app.api import create_app

app = create_app(AppConfig())
client = TestClient(app)
resp = client.get('/api/config')
assert resp.status_code == 200
data = resp.json()
assert 'crawler' in data
assert 'analysis' in data
print('GET /api/config OK')
"`

- [ ] **Step 3: Commit**

```bash
git add app/api/router/config.py
git commit -m "feat: add config API endpoints (GET/PUT /api/config)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: CLI serve command + script entry

**Files:**
- Create: `app/cli/serve_cmd.py`
- Modify: `app/cli/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create serve_cmd.py**

Create `app/cli/serve_cmd.py`:
```python
"""bilianalysis serve - start the API server."""
import typer

serve_app = typer.Typer(name="serve", help="Start the API server")


@serve_app.callback(invoke_without_command=True)
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Listen port"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Start the BiliAnalysis API server."""
    import uvicorn
    from bilianalysis.config import load_config
    from app.api import create_app

    config = load_config(config_path)
    app = create_app(config)

    print(f"BiliAnalysis API v0.1.0")
    print(f"  API:  http://127.0.0.1:{port}")
    print(f"  Docs: http://127.0.0.1:{port}/docs")
    print(f"  Engine: {config.analysis.engine}")
    print()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

- [ ] **Step 2: Update app/cli/__init__.py**

Read the file first, then ADD at the bottom:
```python
from app.cli.serve_cmd import serve_app
app.add_typer(serve_app, name="serve", help="Start API server")
```

- [ ] **Step 3: Update pyproject.toml**

Add to `[project.scripts]`:
```toml
[project.scripts]
bilianalysis = "app.cli:app"
bilianalysis-serve = "app.cli.serve_cmd:serve"
```

- [ ] **Step 4: Verify CLI**

Run: `uv run bilianalysis --help`
Expected: show `serve` command in addition to `schedule`

Run: `uv run bilianalysis serve --help`
Expected: show `--port` and `--config` options

- [ ] **Step 5: Commit**

```bash
git add app/cli/serve_cmd.py app/cli/__init__.py pyproject.toml
git commit -m "feat: add 'bilianalysis serve' CLI command

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Integration tests + final verification

**Files:**
- Create: `tests/test_api.py`

- [ ] **Step 1: Create test file**

Create `tests/test_api.py`:
```python
"""Integration tests for BiliAnalysis API."""
import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from bilianalysis.config.model import AppConfig
from app.api import create_app


@pytest.fixture
def client():
    config = AppConfig()
    app = create_app(config)
    return TestClient(app)


class TestHealthAndConfig:
    def test_config_get(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "crawler" in data
        assert "analysis" in data
        assert "data" in data
        assert "scheduler" in data

    def test_config_put_valid(self, client):
        resp = client.put("/api/config", json={
            "section": "crawler",
            "values": {"mode": "concurrent"},
            "persist": False,
        })
        assert resp.status_code == 200
        assert resp.json()["persisted"] is False

    def test_config_put_invalid_section(self, client):
        resp = client.put("/api/config", json={
            "section": "nonexistent",
            "values": {},
            "persist": False,
        })
        assert resp.status_code == 400

    def test_config_put_invalid_field(self, client):
        resp = client.put("/api/config", json={
            "section": "crawler",
            "values": {"nonexistent_field": 123},
            "persist": False,
        })
        assert resp.status_code == 400


class TestCrawlerRoutes:
    def test_get_crawler_status(self, client):
        resp = client.get("/api/crawler")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_weeks" in data
        assert "is_running" in data


class TestAnalysisRoutes:
    def test_get_analysis_overview(self, client):
        resp = client.get("/api/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "last_clean" in data

    def test_get_analysis_routes_exist(self, client):
        for path in ["/api/analysis/stats", "/api/analysis/clusters",
                      "/api/analysis/predictions"]:
            resp = client.get(path)
            # May fail with engine unavailable but should be 503, not 404
            assert resp.status_code != 404, f"{path} returned 404"


class TestTasksRoutes:
    def test_list_tasks_empty(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipelines"] == []

    def test_list_tasks_with_pipelines(self):
        config = AppConfig()
        from bilianalysis.config.model import SchedulerConfig, PipelineConfig
        config.scheduler = SchedulerConfig(
            pipelines={
                "full": PipelineConfig(schedule="0 12 * * 6", steps=["crawl"]),
            }
        )
        app = create_app(config)
        client = TestClient(app)
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pipelines"]) == 1
        assert data["pipelines"][0]["name"] == "full"


class TestTaskHistory:
    def test_history_empty(self, client):
        resp = client.get("/api/tasks/full/history")
        # May 404 if pipeline doesn't exist
        assert resp.status_code in (200, 404)

    def test_history_nonexistent_pipeline(self, client):
        resp = client.get("/api/tasks/nonexistent/history")
        assert resp.status_code == 404


class TestErrorHandling:
    def test_404_on_unregistered_route(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_app_error_response_format(self, client):
        resp = client.put("/api/config", json={
            "section": "nonexistent",
            "values": {},
        })
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
```

- [ ] **Step 2: Run API tests**

Run: `uv run pytest tests/test_api.py -v`
Expected: ~13 PASS

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (~116 total)

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test: add API integration tests (13 tests)

Co-Authored-By: Claude <noreply@anthropic.com>"
```
