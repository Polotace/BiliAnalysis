"""爬虫 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("crawl")
class CrawlTask(Task):
    name = "crawl"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            from bilianalysis.crawler import CrawlRunner
            report = await CrawlRunner(ctx.config.crawler)
            return TaskResult(
                task_name="crawl", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "crawled": report.crawled,
                    "skipped": report.skipped,
                    "failed": report.failed,
                    "total": report.total,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="crawl", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
