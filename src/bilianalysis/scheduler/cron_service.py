"""常驻调度服务——纯 schedule 定时触发，不依赖 Web 框架。"""
import asyncio
import logging
import threading
import time
from collections import deque

import schedule

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.models import RunRecord

logger = logging.getLogger("bilianalysis.scheduler")


class CronService:
    """常驻调度服务。

    后台线程轮询 schedule 库，到点时通过 run_coroutine_threadsafe
    提交到 asyncio event loop。不含 FastAPI —— Web 层由 app/api.py 负责。
    """

    def __init__(self, config: AppConfig, max_history: int = 100):
        self.config = config
        self.runner = PipelineRunner(config)
        self._history: deque[RunRecord] = deque(maxlen=max_history)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    # ── 公开属性 ──

    @property
    def history(self) -> list[RunRecord]:
        """执行历史（最近 max_history 条）。"""
        return list(self._history)

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        """当前绑定的 event loop（供 app/api.py 注入 cron 回调）。"""
        return self._loop

    # ── schedule 集成 ──

    def setup_schedule(self) -> None:
        """根据配置注册所有 cron 定时任务。幂等（先清后建）。"""
        schedule.clear()
        for name, pipeline in self.config.scheduler.pipelines.items():
            if pipeline.schedule:
                self._register_schedule_job(name, pipeline.schedule)
                logger.info("Registered cron: %s -> %s", name, pipeline.schedule)

    def _register_schedule_job(self, name: str, cron_expr: str) -> None:
        """将 5 字段 cron 表达式转换为 schedule 库调用。"""
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning("Invalid cron expr for '%s': %s", name, cron_expr)
            return

        minute, hour, dom, month, dow = parts

        job = schedule.every()
        if dow != "*":
            day_names = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            try:
                d = int(dow)
                if 0 <= d <= 6:
                    job = getattr(job, day_names[d])
                else:
                    job = job.day
            except ValueError:
                job = job.day
        else:
            job = job.day

        if hour != "*" and minute != "*":
            job = job.at(f"{hour.zfill(2)}:{minute.zfill(2)}")

        job.do(lambda n=name: self._trigger_cron(n))

    def _trigger_cron(self, name: str) -> None:
        """cron 触发——从后台线程提交到 event loop。"""
        if self._loop is None:
            logger.error("Event loop not set, cannot trigger %s", name)
            return
        asyncio.run_coroutine_threadsafe(
            self.execute_pipeline(name, "cron"), self._loop
        )

    async def execute_pipeline(self, name: str, trigger: str) -> RunRecord:
        """执行流水线并记录历史。公开方法，CLI / API 均可调用。"""
        logger.info("Pipeline '%s' triggered by %s", name, trigger)
        record = await self.runner.run(name, trigger=trigger)
        self._history.append(record)
        status_icon = "OK" if record.status == "success" else "FAIL"
        elapsed = (record.finished_at - record.started_at).total_seconds() if record.finished_at else 0
        logger.info("%s Pipeline '%s': %s in %.1fs", status_icon, name, record.status, elapsed)
        return record

    # ── 生命周期 ──

    def start_scheduler(self, loop: asyncio.AbstractEventLoop) -> None:
        """启动后台 schedule 轮询线程。需先调用 setup_schedule()。"""
        self._loop = loop
        self._running = True

        def _run_schedule():
            while self._running:
                schedule.run_pending()
                time.sleep(1)

        thread = threading.Thread(target=_run_schedule, daemon=True)
        thread.start()
        logger.info("Scheduler background thread started")

    def stop(self) -> None:
        """停止调度器。"""
        self._running = False
        schedule.clear()
        logger.info("Scheduler stopped")
