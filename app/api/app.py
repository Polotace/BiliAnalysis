"""FastAPI application factory."""
import asyncio
import logging
import sys
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
    async def _spark_health_check(app: FastAPI):
        """Background task: ping Spark Connect with retries, stop server on failure."""
        cfg = config.analysis

        if cfg.spark_ping_timeout <= 0:
            print("[spark] Health check disabled (spark_ping_timeout=0)")
            return

        # Give the server a moment to finish binding its port
        await asyncio.sleep(2)

        print(f"[spark] Checking connectivity to {cfg.spark_remote} "
              f"(timeout={cfg.spark_ping_timeout}s, retries={cfg.spark_ping_retries}) …")

        # Reuse the API engine singleton — avoids orphan SparkSession
        from api.deps import _analysis_engine
        engine = _analysis_engine
        if engine is None:
            from bilianalysis.engine import create_engine
            engine = create_engine(config)

        for attempt in range(1, cfg.spark_ping_retries + 1):
            try:
                engine.ping(timeout_seconds=cfg.spark_ping_timeout)
                logger.info("Spark Connect ping OK (%s)", cfg.spark_remote)
                print(f"[spark] Connected to {cfg.spark_remote}")
                break  # Spark OK, proceed to HDFS check
            except ConnectionError as exc:
                if attempt < cfg.spark_ping_retries:
                    delay = cfg.spark_ping_retry_delay
                    logger.warning(
                        "Spark ping attempt %d/%d failed (%s), retrying in %.0fs …",
                        attempt, cfg.spark_ping_retries, exc, delay,
                    )
                    print(f"[spark] Attempt {attempt}/{cfg.spark_ping_retries} failed: {exc}")
                    print(f"[spark] Retrying in {delay:.0f}s …")
                    await asyncio.sleep(delay)
                else:
                    logger.critical(
                        "Spark Connect unreachable after %d attempts — shutting down",
                        cfg.spark_ping_retries,
                    )
                    print(f"[spark] FATAL: {cfg.spark_ping_retries} attempts failed. "
                          f"Spark Connect at {cfg.spark_remote} is unreachable. "
                          f"Shutting down.")
                    sys.exit(1)
            except Exception as exc:
                # Unexpected error (not a connectivity issue) — log and exit
                logger.exception("Spark health check aborted: %s", exc)
                print(f"[spark] FATAL: unexpected error: {exc}")
                sys.exit(1)

        # Spark is up — now check HDFS
        try:
            if hasattr(engine, "ping_hdfs"):
                result = engine.ping_hdfs()
                logger.info("HDFS ping OK via %s (%s)", result["backend"], cfg.webhdfs_url)
                print(f"[spark] HDFS reachable via {result['backend']} ({cfg.webhdfs_url})")
        except Exception as exc:
            logger.warning("HDFS ping failed: %s", exc)
            print(f"[spark] WARNING: HDFS unreachable ({exc})")

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        """Startup: create DB tables, spawn Spark health check."""
        from api.deps import _get_sessionmaker
        from api.db.schema import Base
        import api.db.user_schema  # noqa: F401 — register User table
        sm = _get_sessionmaker()
        async with sm() as session:
            async with session.bind.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        # Spawn async Spark connectivity check (non-blocking, retries in background)
        if config.analysis.engine == "spark" and config.analysis.spark_remote:
            app.state._spark_check_task = asyncio.create_task(
                _spark_health_check(app)
            )

        yield

        # Shutdown: cancel pending health check, retrieve exception to suppress warning
        task = getattr(app.state, "_spark_check_task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass

    from api.config import ApiSettings
    import secrets
    api_settings = ApiSettings()
    if not api_settings.session_secret_key:
        api_settings.session_secret_key = secrets.token_urlsafe(32)

    app = FastAPI(title="BiliAnalysis API", version="0.1.0", lifespan=_lifespan)

    # Session middleware (must be before CORS)
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=api_settings.session_secret_key)

    # Runtime shared state
    app.state.config = config
    app.state.api_settings = api_settings
    app.state.run_history: deque[RunRecord] = deque(maxlen=200)

    # CORS (frontend dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
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
    from api.router import auth
    app.include_router(auth.router, prefix="/api")
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
