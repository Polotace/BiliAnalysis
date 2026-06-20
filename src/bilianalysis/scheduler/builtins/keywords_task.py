"""关键词提取 Task。"""
import json
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register
from bilianalysis.nlp import build_keywords_report


@register("keywords")
class KeywordsTask(Task):
    name = "keywords"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = build_keywords_report(ctx.config.data.processed_dir)
            rd = Path(ctx.config.data.reports_dir)
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "keywords_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8")
            return TaskResult(
                task_name="keywords", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "global_keywords": len(report.global_.keywords),
                    "weeks_with_keywords": len(report.by_week),
                    "categories_with_keywords": len(report.by_category),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="keywords", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
