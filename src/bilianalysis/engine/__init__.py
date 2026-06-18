"""分析引擎模块。"""
from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import (
    AnalysisEngine,
    CleanReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend, StatReport,
    ClusterGroup, ClusterResult, ClusterReport,
    PredictionResult, PredictionReport,
)
from bilianalysis.engine.pandas_engine import PandasEngine

try:
    from bilianalysis.engine.spark_engine import SparkEngine
    _HAS_SPARK = True
except ImportError:
    _HAS_SPARK = False
    SparkEngine = None  # type: ignore


def create_engine(config: AppConfig) -> AnalysisEngine:
    """根据配置创建分析引擎实例。"""
    if config.analysis.engine == "spark":
        if not _HAS_SPARK:
            raise ImportError("PySpark is not installed. Install it firstly.")
        return SparkEngine(config.data)
    return PandasEngine(config.data)


__all__ = [
    "AnalysisEngine", "PandasEngine", "SparkEngine", "create_engine",
    "CleanReport",
    "OverallStats", "CategoryStats", "CreatorStats", "WeeklyTrend", "StatReport",
    "ClusterGroup", "ClusterResult", "ClusterReport",
    "PredictionResult", "PredictionReport",
]
