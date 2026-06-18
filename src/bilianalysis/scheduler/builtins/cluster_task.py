"""聚类分析 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("clustering")
class ClusteringTask(Task):
    name = "clustering"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.clustering()
            return TaskResult(
                task_name="clustering", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "k": report.clusters.k,
                    "silhouette_score": report.clusters.silhouette_score,
                    "cluster_count": len(report.clusters.clusters),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="clustering", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
