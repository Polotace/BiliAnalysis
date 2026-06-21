"""Analysis endpoints: /api/analysis and sub-routes."""
import asyncio
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException

from bilianalysis.config.model import AppConfig
from bilianalysis.nlp import KeywordsReport as NLPKeywordsReport
from bilianalysis.engine.base import (
    AnalysisEngine, StatReport, ClusterReport, PredictionReport,
    ModelComparisonReport,
)
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from api.deps import get_config, get_runner, get_engine, require_admin
from api.history import save_record
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
    """Raise 503 if no processed data or cached reports exist yet."""
    rd = _reports_dir(config)
    pd = Path(config.data.processed_dir)
    has_cache = (rd / "stats_report.json").exists()
    has_parquet = (pd / "Weekly.parquet").exists()
    if not has_cache and not has_parquet:
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
        last_model_comparison=_read_json(rd / "model_comparison_report.json"),
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
    _check_data_ready(config)
    try:
        return engine.statistics()
    except (FileNotFoundError, OSError):
        raise HTTPException(
            status_code=503,
            detail="暂无数据，请先触发一次数据采集与分析",
        )


@router.get("/analysis/clusters", response_model=ClusterReport)
async def get_clusters(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get clustering report."""
    cached = _read_json(_reports_dir(config) / "cluster_report.json")
    if cached:
        return ClusterReport(**cached)
    _check_data_ready(config)
    try:
        return engine.clustering()
    except (FileNotFoundError, OSError):
        raise HTTPException(
            status_code=503,
            detail="暂无数据，请先触发一次数据采集与分析",
        )


@router.get("/analysis/predictions", response_model=PredictionReport)
async def get_predictions(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get prediction report."""
    cached = _read_json(_reports_dir(config) / "prediction_report.json")
    if cached:
        return PredictionReport(**cached)
    _check_data_ready(config)
    try:
        return engine.prediction()
    except (FileNotFoundError, OSError):
        raise HTTPException(
            status_code=503,
            detail="暂无数据，请先触发一次数据采集与分析",
        )


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
async def get_model_comparison(
    config: Annotated[AppConfig, Depends(get_config)],
    engine: Annotated[AnalysisEngine, Depends(get_engine)],
):
    """Get model comparison report.

    Reads from cached report JSON if available (sub-ms); falls back to
    live engine computation (~60-90s for 5 models with 5-fold CV).
    """
    cached = _read_json(_reports_dir(config) / "model_comparison_report.json")
    if cached:
        return ModelComparisonReport(**cached)
    _check_data_ready(config)
    try:
        return engine.model_comparison()
    except (FileNotFoundError, OSError):
        raise HTTPException(
            status_code=503,
            detail="暂无数据，请先触发一次数据采集与分析",
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=503,
            detail="当前分析引擎不支持模型对比 (需要 Pandas 引擎)",
        )
