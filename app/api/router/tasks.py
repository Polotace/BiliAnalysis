"""Task/pipeline endpoints: /api/tasks"""
import asyncio
from datetime import datetime, timezone
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
