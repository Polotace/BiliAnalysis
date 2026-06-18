"""调度系统运行时模型。"""
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from bilianalysis.scheduler.task import TaskResult

TRIGGER_TYPE = Literal["cron", "manual"]


class RunRecord(BaseModel):
    """一次流水线执行记录。"""
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    pipeline: str
    trigger: TRIGGER_TYPE
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: Literal["running", "success", "failed"] = "running"
    step_results: list[TaskResult] = []
