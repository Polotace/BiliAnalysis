"""内置 Task 实现——导入即注册。"""
from .crawl_task import CrawlTask        # noqa: F401
from .clean_task import CleanDataTask     # noqa: F401
from .stats_task import StatisticsTask    # noqa: F401
from .cluster_task import ClusteringTask  # noqa: F401
from .predict_task import PredictionTask  # noqa: F401
from .warehouse_task import WarehouseTask  # noqa: F401
