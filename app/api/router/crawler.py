"""Crawler endpoints: /api/crawler"""
import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.crawler import CrawlRunner
from bilianalysis.crawler.storage import load_progress
from bilianalysis.scheduler.models import RunRecord
from api.deps import get_config
from api.schemas import TaskTriggerResponse, CrawlerStatus

router = APIRouter(tags=["crawler"])


@router.post("/crawler", status_code=202, response_model=TaskTriggerResponse)
async def trigger_crawl(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
):
    """Trigger a crawl task in the background."""
    record = RunRecord(
        pipeline="crawler", trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    request.app.state.run_history.append(record)

    async def _run():
        try:
            await CrawlRunner(config.crawler)
            record.status = "success"
        except Exception as exc:
            record.status = "failed"
        finally:
            record.finished_at = datetime.now(timezone.utc)

    asyncio.create_task(_run())
    return TaskTriggerResponse(run_id=record.run_id, pipeline="crawler")


@router.get("/crawler", response_model=CrawlerStatus)
async def get_crawler_status(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
):
    """Get crawler progress from progress.json and run history."""
    progress = await load_progress()
    is_running = any(
        r.pipeline == "crawler" and r.status == "running"
        for r in request.app.state.run_history
    )
    return CrawlerStatus(
        total_weeks=len(progress.crawled) + len(progress.failed),
        crawled=len(progress.crawled),
        failed={int(k): v for k, v in progress.failed.items()},
        last_run=progress.last_run,
        is_running=is_running,
    )
