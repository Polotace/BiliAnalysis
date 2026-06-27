"""FastAPI dependency injection for config, runner, engine, and database sessions."""
from typing import Annotated

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.config import ApiSettings
from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.runner import PipelineRunner

_engine = None
_sessionmaker = None


def _get_sessionmaker():
    """Lazy-init the async engine and sessionmaker from ApiSettings."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = ApiSettings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def get_db():
    """Yield an AsyncSession. Session lifecycle = request scope."""
    sm = _get_sessionmaker()
    async with sm() as session:
        yield session


def get_config(request: Request) -> AppConfig:
    """Get the runtime AppConfig stored on app.state."""
    return request.app.state.config


def get_runner(
    config: Annotated[AppConfig, Depends(get_config)],
) -> PipelineRunner:
    """Create a PipelineRunner from the current config."""
    return PipelineRunner(config)


_analysis_engine: AnalysisEngine | None = None


def get_engine(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AnalysisEngine:
    """Return the application-scoped AnalysisEngine singleton.

    Created once on first call and reused for all subsequent requests.
    PandasEngine is cheap; SparkEngine holds a single SparkSession that
    must not be created per-request.
    """
    global _analysis_engine
    if _analysis_engine is None:
        from bilianalysis.engine import create_engine
        _analysis_engine = create_engine(config)
    return _analysis_engine
