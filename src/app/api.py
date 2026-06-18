"""FastAPI 应用工厂——将 CronService 暴露为 HTTP API。"""
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from bilianalysis.scheduler.cron_service import CronService
from bilianalysis.scheduler.models import RunRecord


def create_scheduler_app(service: CronService) -> FastAPI:
    """基于 CronService 实例创建 FastAPI 应用。

    Usage:
        service = CronService(config)
        service.setup_schedule()
        app = create_scheduler_app(service)
        uvicorn.run(app, host="127.0.0.1", port=8080)
    """
    app = FastAPI(title="BiliAnalysis Scheduler", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok", "pipelines": list(service.config.scheduler.pipelines.keys())}

    @app.get("/pipelines")
    async def list_pipelines():
        result = {}
        for name, pl in service.config.scheduler.pipelines.items():
            result[name] = {
                "schedule": pl.schedule,
                "steps": pl.steps,
                "step_failure": pl.step_failure,
            }
        return result

    @app.get("/pipelines/{name}/runs")
    async def pipeline_runs(name: str, limit: int = 20):
        if name not in service.config.scheduler.pipelines:
            raise HTTPException(404, f"Pipeline '{name}' not found")
        runs = [r for r in service.history if r.pipeline == name]
        return runs[-limit:]

    @app.post("/pipelines/{name}/run")
    async def trigger_pipeline(name: str):
        if name not in service.config.scheduler.pipelines:
            raise HTTPException(404, f"Pipeline '{name}' not found")
        # 后台执行，不阻塞响应
        asyncio.create_task(service.execute_pipeline(name, "manual"))
        record = RunRecord(pipeline=name, trigger="manual")
        service._history.append(record)
        return JSONResponse(
            status_code=202,
            content={"run_id": record.run_id, "pipeline": name, "status": "accepted"},
        )

    return app
