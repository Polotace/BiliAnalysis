"""统计分析 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("statistics")
class StatisticsTask(Task):
    name = "statistics"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.statistics()
            return TaskResult(
                task_name="statistics", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "total_videos": report.overall.total_videos,
                    "avg_view": report.overall.avg_view,
                    "avg_like_rate": report.overall.avg_like_rate,
                    "category_count": len(report.by_category),
                    "creator_count": len(report.by_creator),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="statistics", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
