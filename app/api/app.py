"""FastAPI application factory."""
import logging
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from app.api.errors import AppError

logger = logging.getLogger("bilianalysis.api")


def create_app(config: AppConfig) -> FastAPI:
    """Create a configured FastAPI application.

    Args:
        config: The application configuration.

    Returns:
        A FastAPI app ready for uvicorn.run().
    """
    app = FastAPI(title="BiliAnalysis API", version="0.1.0")

    # Runtime shared state
    app.state.config = config
    app.state.run_history: deque[RunRecord] = deque(maxlen=200)

    # CORS (frontend dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from app.api.router import crawler, analysis, tasks, config as config_router
    app.include_router(crawler.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(config_router.router, prefix="/api")

    # Register error handlers
    _register_error_handlers(app)

    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
