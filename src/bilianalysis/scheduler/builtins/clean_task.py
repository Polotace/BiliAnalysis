"""数据清洗 Task。"""
import asyncio
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("clean_data")
class CleanDataTask(Task):
    name = "clean_data"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = await asyncio.to_thread(
                lambda: asyncio.run(ctx.engine.clean_data()))
            return TaskResult(
                task_name="clean_data", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "total_weeks": report.total_weeks,
                    "total_videos": report.total_videos,
                    "duplicates_dropped": report.duplicates_dropped,
                    "outliers_flagged": report.outliers_flagged,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="clean_data", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
