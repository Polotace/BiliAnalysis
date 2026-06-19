"""数据仓库构建 Task。"""
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskContext, TaskResult
from bilianalysis.scheduler.registry import register


@register("build_warehouse")
class WarehouseTask(Task):
    name = "build_warehouse"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            from bilianalysis.warehouse import build_warehouse

            raw_dir = Path(ctx.config.data.raw_dir)
            warehouse_dir = Path(ctx.config.data.processed_dir).parent / "warehouse"
            report = build_warehouse(raw_dir, warehouse_dir)

            return TaskResult(
                task_name="build_warehouse", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "weeks_processed": report.weeks_processed,
                    "weeks_skipped": report.weeks_skipped,
                    "tables_written": report.tables_written,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="build_warehouse", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
