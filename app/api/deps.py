"""FastAPI dependency injection for config, runner, and engine."""
from typing import Annotated

from fastapi import Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.runner import PipelineRunner


def get_config(request: Request) -> AppConfig:
    """Get the runtime AppConfig stored on app.state."""
    return request.app.state.config


def get_runner(
    config: Annotated[AppConfig, Depends(get_config)],
) -> PipelineRunner:
    """Create a PipelineRunner from the current config."""
    return PipelineRunner(config)


def get_engine(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AnalysisEngine:
    """Create an AnalysisEngine from the current config.

    Uses the create_engine() factory to pick Pandas or Spark.
    """
    from bilianalysis.engine import create_engine
    return create_engine(config)
