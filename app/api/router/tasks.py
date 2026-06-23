"""Task/pipeline endpoints: /api/tasks"""
import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from api.deps import get_config, get_runner, require_admin
from api.errors import PipelineNotFound
from api.history import save_record
from bilianalysis.engine import create_engine
from bilianalysis.scheduler.registry import get_task
from bilianalysis.scheduler.task import TaskContext
from api.schemas import (
    TaskTriggerResponse, PipelineInfo, PipelineListResponse, RunHistoryItem,
)

router = APIRouter(tags=["tasks"])


@router.get("/run/{run_id}", response_model=RunHistoryItem)
async def get_run(
    run_id: str,
    config: Annotated[AppConfig, Depends(get_config)],
):
    """Look up a single run record by run_id."""
    from api.history import load_records
    rows = load_records()
    for row in rows:
        if row["run_id"] == run_id:
            return RunHistoryItem(
                run_id=row["run_id"],
                pipeline=row["pipeline"],
                trigger=row.get("trigger", "manual"),
                started_at=row.get("started_at", ""),
                finished_at=row.get("finished_at") or None,
                status=row.get("status", "unknown"),
                step_count=int(row.get("step_count", 0)),
                failed_step=row.get("failed_step") or None,
                error=row.get("error") or None,
            )
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.get("/task")
async def list_task_names():
    """List all registered task names."""
    import bilianalysis.scheduler.builtins  # noqa: F401
    import api.tasks                  # noqa: F401
    from bilianalysis.scheduler.registry import list_tasks
    return {"tasks": list_tasks()}


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
    _admin: None = Depends(require_admin),
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


@router.get("/tasks/history", response_model=list[RunHistoryItem])
async def all_history(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    limit: int = 50,
):
    """Get all execution history from CSV, newest first."""
    from api.history import load_records
    rows = load_records()
    items = []
    for row in rows[:limit]:
        items.append(RunHistoryItem(
            run_id=row["run_id"],
            pipeline=row["pipeline"],
            trigger=row.get("trigger", "manual"),
            started_at=row.get("started_at", ""),
            finished_at=row.get("finished_at") or None,
            status=row.get("status", "unknown"),
            step_count=int(row.get("step_count", 0)),
            failed_step=row.get("failed_step") or None,
            error=row.get("error") or None,
        ))
    return items


@router.get("/tasks/{name}/history", response_model=list[RunHistoryItem])
async def pipeline_history(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    limit: int = 50,
):
    """Get execution history for a pipeline or single task (from CSV)."""
    if not name.startswith("_task_") and name not in config.scheduler.pipelines:
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
            error=row.get("error") or None,
        ))
        if len(items) >= limit:
            break
    return items


@router.post("/task/{name}", status_code=202, response_model=TaskTriggerResponse)
async def run_single_task(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    _admin: None = Depends(require_admin),
):
    """Run a single registered task independently (not as part of a pipeline)."""
    import bilianalysis.scheduler.builtins  # noqa: F401
    import api.tasks                  # noqa: F401

    try:
        task_cls = get_task(name)
    except KeyError:
        raise PipelineNotFound(name)

    record = RunRecord(
        pipeline=f"_task_{name}", trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            ctx = TaskContext(config=config)
            ctx.engine = create_engine(config)
            result = await task_cls().run(ctx)
            record.status = result.status
            record.step_results = [result]
        except Exception:
            record.status = "failed"
        finally:
            record.finished_at = datetime.now(timezone.utc)
            save_record(record)
            # Stop SparkSession if engine has one (may be None — lazy init)
            if ctx.engine is not None and hasattr(ctx.engine, "_spark"):
                spark = ctx.engine._spark
                if spark is not None:
                    try:
                        spark.stop()
                    except Exception:
                        pass

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline=f"_task_{name}")
