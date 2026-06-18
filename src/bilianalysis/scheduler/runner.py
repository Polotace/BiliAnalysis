"""PipelineRunner——按序执行 Task 列表。"""
from datetime import datetime, timezone
from typing import Literal
from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.task import TaskContext, TaskResult
from bilianalysis.scheduler.registry import get_task
from bilianalysis.scheduler.models import RunRecord, TRIGGER_TYPE


class PipelineRunner:
    """流水线执行器。惰性创建引擎，finally 块清理。"""

    def __init__(self, config: AppConfig):
        self._config = config
        self._engine: AnalysisEngine | None = None

    def _ensure_engine(self) -> AnalysisEngine:
        """惰性创建分析引擎（Pandas 或 Spark）。"""
        if self._engine is None:
            from bilianalysis.engine import create_engine
            return create_engine(self._config)
        else:
            return self._engine

    async def run(self, name: str, trigger: TRIGGER_TYPE = "manual") -> RunRecord:
        """执行一条流水线。"""
        pipeline = self._config.scheduler.pipelines[name]
        record = RunRecord(pipeline=name, trigger=trigger)
        ctx = TaskContext(config=self._config)

        try:
            for step_name in pipeline.steps:
                task_cls = get_task(step_name)
                task = task_cls()

                # 惰性注入引擎
                if ctx.engine is None:
                    ctx.engine = self._ensure_engine()

                result = await task.run(ctx)
                ctx.previous[step_name] = result
                record.step_results.append(result)

                if result.status == "failed":
                    if pipeline.step_failure == "stop":
                        break
                    elif pipeline.step_failure == "retry":
                        success = False
                        for _ in range(pipeline.max_retries):
                            result = await task.run(ctx)
                            ctx.previous[step_name] = result
                            record.step_results[-1] = result
                            if result.status == "success":
                                success = True
                                break
                        if not success:
                            break
                    # "skip" → continue to next step

            # 判断整体状态
            all_success = all(
                r.status in ("success", "skipped") for r in record.step_results
            )
            record.status = "success" if all_success else "failed"
        except Exception as exc:
            record.status = "failed"
            record.step_results.append(TaskResult(
                task_name="pipeline", status="failed",
                duration_seconds=0, error=str(exc),
            ))
        finally:
            record.finished_at = datetime.now(timezone.utc)
            # 清理 Spark 引擎
            if self._engine is not None and hasattr(self._engine, "_spark"):
                try:
                    self._engine._spark.stop()
                except Exception:
                    pass

        return record
