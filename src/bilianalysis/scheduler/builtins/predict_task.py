"""回归预测 Task。"""
import asyncio
import json
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("prediction")
class PredictionTask(Task):
    name = "prediction"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = await asyncio.to_thread(ctx.engine.prediction)
            rd = Path(ctx.config.data.reports_dir)
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "prediction_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8")
            return TaskResult(
                task_name="prediction", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "view_r2": report.view_predict.r2_score,
                    "view_mae": report.view_predict.mae,
                    "like_r2": report.like_predict.r2_score,
                    "like_mae": report.like_predict.mae,
                },
            )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return TaskResult(
                task_name="prediction", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc) or repr(exc),
            )
