"""FastAPI application factory."""
import logging
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from api.errors import AppError

logger = logging.getLogger("bilianalysis.api")


def create_app(config: AppConfig) -> FastAPI:
    """Create a configured FastAPI application.

    Args:
        config: The application configuration.

    Returns:
        A FastAPI app ready for uvicorn.run().
    """
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        """Startup: create DB tables if they don't exist. Shutdown: no-op."""
        from api.deps import _get_sessionmaker
        from api.db.schema import Base
        sm = _get_sessionmaker()
        async with sm() as session:
            async with session.bind.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        yield

    app = FastAPI(title="BiliAnalysis API", version="0.1.0", lifespan=_lifespan)

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
    from api.router import analysis
    from api.router import categories
    from api.router import config as config_router
    from api.router import crawler
    from api.router import creators
    from api.router import tasks
    from api.router import videos
    from api.router import weeks
    from api.router import db_load
    from api.router import proxy
    app.include_router(categories.router, prefix="/api")
    app.include_router(crawler.router, prefix="/api")
    app.include_router(creators.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(videos.router, prefix="/api")
    app.include_router(weeks.router, prefix="/api")
    app.include_router(config_router.router, prefix="/api")
    app.include_router(db_load.router, prefix="/api")
    app.include_router(proxy.router, prefix="/api")

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
