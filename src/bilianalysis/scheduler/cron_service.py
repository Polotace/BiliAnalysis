"""常驻调度服务——schedule 定时 + FastAPI 手动触发。"""
import asyncio
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

import schedule
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.models import RunRecord

logger = logging.getLogger("bilianalysis.scheduler")


class CronService:
    """常驻调度服务。

    主线程跑 FastAPI + uvicorn，后台线程轮询 schedule 库。
    触发时通过 run_coroutine_threadsafe 提交到 event loop。
    """

    def __init__(self, config: AppConfig, max_history: int = 100):
        self.config = config
        self.runner = PipelineRunner(config)
        self._history: deque[RunRecord] = deque(maxlen=max_history)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    # ── schedule 集成 ──

    def _setup_cron_jobs(self) -> None:
        """根据配置注册所有 cron 定时任务。"""
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
            self._execute_pipeline(name, "cron"), self._loop
        )

    async def _execute_pipeline(self, name: str, trigger: str) -> RunRecord:
        """执行流水线并记录历史。"""
        logger.info("Pipeline '%s' triggered by %s", name, trigger)
        record = await self.runner.run(name, trigger=trigger)
        self._history.append(record)
        status_icon = "OK" if record.status == "success" else "FAIL"
        elapsed = (record.finished_at - record.started_at).total_seconds() if record.finished_at else 0
        logger.info("%s Pipeline '%s': %s in %.1fs", status_icon, name, record.status, elapsed)
        return record

    # ── FastAPI app ──

    def create_app(self) -> FastAPI:
        """创建 FastAPI 应用。"""
        app = FastAPI(title="BiliAnalysis Scheduler", version="0.1.0")
        service = self

        @app.get("/health")
        async def health():
            return {"status": "ok", "pipelines": list(self.config.scheduler.pipelines.keys())}

        @app.get("/pipelines")
        async def list_pipelines():
            result = {}
            for name, pl in self.config.scheduler.pipelines.items():
                result[name] = {
                    "schedule": pl.schedule,
                    "steps": pl.steps,
                    "step_failure": pl.step_failure,
                }
            return result

        @app.get("/pipelines/{name}/runs")
        async def pipeline_runs(name: str, limit: int = 20):
            if name not in self.config.scheduler.pipelines:
                raise HTTPException(404, f"Pipeline '{name}' not found")
            runs = [r for r in self._history if r.pipeline == name]
            return runs[-limit:]

        @app.post("/pipelines/{name}/run")
        async def trigger_pipeline(name: str):
            if name not in self.config.scheduler.pipelines:
                raise HTTPException(404, f"Pipeline '{name}' not found")
            # 后台执行
            asyncio.create_task(service._execute_pipeline(name, "manual"))
            record = RunRecord(pipeline=name, trigger="manual")
            service._history.append(record)
            return JSONResponse(
                status_code=202,
                content={"run_id": record.run_id, "pipeline": name, "status": "accepted"},
            )

        return app

    # ── 启动 / 停止 ──

    def start(self, port: int = 8080) -> None:
        """阻塞式启动 serve 模式。"""
        import uvicorn

        self._running = True
        self._setup_cron_jobs()

        def _run_schedule():
            while self._running:
                schedule.run_pending()
                time.sleep(1)

        thread = threading.Thread(target=_run_schedule, daemon=True)
        thread.start()

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        app = self.create_app()
        logger.info("Scheduler started on http://127.0.0.1:%d", port)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

    def stop(self) -> None:
        """停止服务。"""
        self._running = False
        schedule.clear()
