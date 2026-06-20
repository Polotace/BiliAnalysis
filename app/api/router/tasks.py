"""Task/pipeline endpoints: /api/tasks"""
import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from api.deps import get_config, get_runner
from api.errors import PipelineNotFound
from api.history import save_record
from api.schemas import (
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

    record = RunRecord(
        pipeline=name, trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            import bilianalysis.scheduler.builtins  # noqa: F401
            result = await runner.run(name, trigger="manual")
            record.status = result.status
            record.step_results = result.step_results
        except Exception:
            record.status = "failed"
        finally:
            record.finished_at = datetime.now(timezone.utc)
            save_record(record)

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline=name)


@router.get("/tasks/{name}/history", response_model=list[RunHistoryItem])
async def pipeline_history(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    limit: int = 50,
):
    """Get execution history for a pipeline (from CSV)."""
    if name not in config.scheduler.pipelines:
        raise PipelineNotFound(name)

    from api.history import load_records
    rows = load_records()
    items = []
    for row in rows:
        if row.get("pipeline") != name:
            continue
        items.append(RunHistoryItem(
            run_id=row["run_id"],
            pipeline=row["pipeline"],
            trigger=row.get("trigger", "manual"),
            started_at=row.get("started_at", ""),
            finished_at=row.get("finished_at") or None,
            status=row.get("status", "unknown"),
            step_count=int(row.get("step_count", 0)),
            failed_step=row.get("failed_step") or None,
        ))
        if len(items) >= limit:
            break
    return items
