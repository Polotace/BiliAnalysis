"""配置数据模型。纯 Pydantic，无 I/O 依赖。"""
from pydantic import BaseModel
from typing import Literal


class CrawlerSection(BaseModel):
    """爬虫配置节"""
    mode: Literal["sequential", "concurrent"] = "sequential"
    concurrency: int = 3
    request_delay: float = 2.5
    max_retries: int = 3
    retry_delay: float = 1.0


class AnalysisSection(BaseModel):
    """分析引擎配置节"""
    engine: Literal["pandas", "spark"] = "pandas"


class DataSection(BaseModel):
    """数据路径配置节"""
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    reports_dir: str = "data/reports"


class AppConfig(BaseModel):
    """应用根配置"""
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
