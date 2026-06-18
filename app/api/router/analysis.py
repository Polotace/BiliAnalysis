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
    from datetime import datetime, timezone

    record = RunRecord(
        pipeline="analysis", trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            import bilianalysis.scheduler.builtins  # noqa: F401
            result = await runner.run("analysis", trigger="manual")
            record.status = result.status
            record.step_results = result.step_results
        except Exception:
            record.status = "failed"
        finally:
            record.finished_at = datetime.now(timezone.utc)

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
