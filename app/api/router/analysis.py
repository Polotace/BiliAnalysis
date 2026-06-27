"""Analysis endpoints: /api/analysis and sub-routes."""
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException

from bilianalysis.config.model import AppConfig
from bilianalysis.nlp import KeywordsReport as NLPKeywordsReport
from bilianalysis.engine.base import (
    StatReport, ClusterReport, PredictionReport, ModelComparisonReport,
)
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from api.deps import get_config, get_runner
from api.auth_session import require_admin
from api.history import save_record
from api.router.tasks import _mark_running, _mark_done
from api.schemas import TaskTriggerResponse, AnalysisOverview

router = APIRouter(tags=["analysis"])


def _reports_dir(config: AppConfig) -> Path:
    return Path(config.data.reports_dir)


def _read_json(path: Path) -> dict | None:
    """Read a JSON file if it exists, return None otherwise."""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _check_data_ready(config: AppConfig) -> None:
    """Raise 503 if no processed data or cached reports exist yet.

    When ``engine=spark`` the processed Parquet lives on HDFS (not the
    local filesystem), so we only check for a cached report.
    """
    rd = _reports_dir(config)
    has_cache = (rd / "stats_report.json").exists()
    if has_cache:
        return

    if config.analysis.engine != "spark":
        # Pandas: check for local Parquet as a fallback signal
        pd = Path(config.data.processed_dir)
        if (pd / "Weekly.parquet").exists():
            return

    raise HTTPException(
        status_code=503,
        detail="暂无数据，请先触发一次数据采集与分析",
    )


@router.post("/analysis", status_code=202, response_model=TaskTriggerResponse)
async def trigger_analysis(
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[PipelineRunner, Depends(get_runner)],
    request: Request,
    _admin: None = Depends(require_admin),
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
            save_record(record)
            _mark_done(record.run_id)

    asyncio.create_task(_run())
    _mark_running(record.run_id, "analysis")
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
        last_keywords=_read_json(rd / "keywords_report.json"),
        last_model_comparison=_read_json(rd / "model_comparison_report.json"),
    )


@router.get("/analysis/stats", response_model=StatReport)
async def get_stats(config: Annotated[AppConfig, Depends(get_config)]):
    """Get statistics report from cache."""
    cached = _read_json(_reports_dir(config) / "stats_report.json")
    if cached:
        return StatReport(**cached)
    raise HTTPException(status_code=503, detail="暂无数据，请先触发一次数据采集与分析")


@router.get("/analysis/clusters", response_model=ClusterReport)
async def get_clusters(config: Annotated[AppConfig, Depends(get_config)]):
    """Get clustering report from cache."""
    cached = _read_json(_reports_dir(config) / "cluster_report.json")
    if cached:
        return ClusterReport(**cached)
    raise HTTPException(status_code=503, detail="暂无数据，请先触发一次数据采集与分析")


@router.get("/analysis/predictions", response_model=PredictionReport)
async def get_predictions(config: Annotated[AppConfig, Depends(get_config)]):
    """Get prediction report from cache."""
    cached = _read_json(_reports_dir(config) / "prediction_report.json")
    if cached:
        return PredictionReport(**cached)
    raise HTTPException(status_code=503, detail="暂无数据，请先触发一次数据采集与分析")


@router.get("/analysis/keywords")
async def get_keywords(config: Annotated[AppConfig, Depends(get_config)]):
    """Get keyword analysis report from cache, or 503 if not generated."""
    cached = _read_json(_reports_dir(config) / "keywords_report.json")
    if cached:
        return cached
    _check_data_ready(config)
    raise HTTPException(
        status_code=503,
        detail="关键词报告尚未生成，请先触发 analysis 流水线",
    )


@router.get("/analysis/models", response_model=ModelComparisonReport)
async def get_model_comparison(config: Annotated[AppConfig, Depends(get_config)]):
    """Get model comparison report from cache."""
    cached = _read_json(_reports_dir(config) / "model_comparison_report.json")
    if cached:
        return ModelComparisonReport(**cached)
    raise HTTPException(status_code=503, detail="模型对比报告尚未生成，请先触发 analysis 流水线 (需要 Pandas 引擎)")
