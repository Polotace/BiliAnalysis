"""分析引擎模块。"""
from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import (
    AnalysisEngine,
    CleanReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend, StatReport,
    ClusterGroup, ClusterResult, ClusterReport,
    PredictionResult, PredictionReport,
    SingleModelResult, FeatureImportanceItem, ModelComparisonReport,
)
from bilianalysis.engine.pandas_engine import PandasEngine

try:
    from bilianalysis.engine.spark_engine import SparkEngine
    _HAS_SPARK = True
except ImportError:
    _HAS_SPARK = False
    SparkEngine = None  # type: ignore


def create_engine(config: AppConfig) -> AnalysisEngine:
    """根据配置创建分析引擎实例。

    - "pandas": PandasEngine（默认，Python 主进程内运行）
    - "spark":  SparkEngine（Spark Connect + HDFS）
    """
    if config.analysis.engine == "spark":
        if not _HAS_SPARK:
            raise ImportError("PySpark is not installed. Install it firstly.")
        if not config.analysis.spark_remote:
            raise ValueError(
                "spark_remote is required when engine=spark. "
                "Set it in config or via SPARK_REMOTE env var."
            )
        if not config.analysis.webhdfs_url:
            raise ValueError("webhdfs_url is required when engine=spark.")
        return SparkEngine(
            config.data,
            spark_remote=config.analysis.spark_remote,
            webhdfs_url=config.analysis.webhdfs_url,
        )
    return PandasEngine(config.data)


__all__ = [
    "AnalysisEngine", "PandasEngine", "SparkEngine", "create_engine",
    "CleanReport",
    "OverallStats", "CategoryStats", "CreatorStats", "WeeklyTrend", "StatReport",
    "ClusterGroup", "ClusterResult", "ClusterReport",
    "PredictionResult", "PredictionReport",
    "SingleModelResult", "FeatureImportanceItem", "ModelComparisonReport",
]
