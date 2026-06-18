"""统计分析 Task。"""
import json
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("statistics")
class StatisticsTask(Task):
    name = "statistics"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.statistics()
            # 写出报告 JSON
            rd = Path(ctx.config.data.reports_dir)
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "stats_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8")
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
