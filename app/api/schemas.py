"""API request/response models. Engine reports reused from bilianalysis.engine.base."""
from datetime import datetime

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
    last_keywords: dict | None = None
    last_model_comparison: dict | None = None


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
    error: str | None = None


# ── Config ──

class ConfigUpdateRequest(BaseModel):
    section: str
    values: dict
    persist: bool = False
