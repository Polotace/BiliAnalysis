"""模型对比 Task。"""
import asyncio
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("model_comparison")
class ModelComparisonTask(Task):
    name = "model_comparison"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = await asyncio.to_thread(ctx.engine.model_comparison)
            rd = Path(ctx.config.data.reports_dir)
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "model_comparison_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8")
            return TaskResult(
                task_name="model_comparison", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "n_samples": report.n_samples,
                    "n_features": report.n_features,
                    "best_model": report.best_model,
                    "best_r2": next(
                        (m.r2_mean for m in report.models
                         if m.model_name == report.best_model), 0.0),
                    "model_count": len(report.models),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="model_comparison", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
