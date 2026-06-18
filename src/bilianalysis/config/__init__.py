"""配置模块。提供 load_config() + AppConfig 数据模型。"""
from .model import (
    AppConfig, CrawlerSection, AnalysisSection, DataSection,
    PipelineConfig, SchedulerConfig,
)
from .loader import load_config

__all__ = [
    "load_config",
    "AppConfig",
    "CrawlerSection",
    "AnalysisSection",
    "DataSection",
    "PipelineConfig",
    "SchedulerConfig",
]
