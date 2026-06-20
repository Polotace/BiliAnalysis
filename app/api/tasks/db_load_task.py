"""数据入库 Task — lives in app/ layer because it needs DB access."""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register
from app.api.db.loader import load_incremental, load_raw_weeks
from app.api.config import ApiSettings


@register("db_load")
class DbLoadTask(Task):
    name = "db_load"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            api_settings = ApiSettings()
            engine = create_async_engine(
                api_settings.database_url,
                pool_size=api_settings.database_pool_size,
            )
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                raw_records = load_raw_weeks(ctx.config.data.raw_dir)
                result = await load_incremental(session, raw_records)

            await engine.dispose()

            return TaskResult(
                task_name="db_load", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "loaded": len(result.get("loaded", [])),
                    "skipped": len(result.get("skipped", [])),
                    "failed": len(result.get("failed", {})),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="db_load", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
