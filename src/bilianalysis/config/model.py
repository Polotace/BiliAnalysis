"""配置数据模型。纯 Pydantic，无 I/O 依赖。"""
from pydantic import BaseModel
from typing import Literal


class CrawlerSection(BaseModel):
    """爬虫配置节"""
    request_delay: float = 2.5
    max_retries: int = 3
    retry_delay: float = 1.0
    cookie: str = ""                             # B站 Cookie（提升请求权重）
    key_refresh_interval: int = 50               # 主动刷新 WBI 密钥的请求间隔（0=不刷新）
    max_requests_per_session: int = 80           # Session 复用上限（0=不限制）


class AnalysisSection(BaseModel):
    """分析引擎配置节"""
    engine: Literal["pandas", "spark"] = "pandas"
    spark_remote: str | None = None            # Spark Connect gRPC 端点 "sc://host:15002"
    webhdfs_url: str | None = None             # WebHDFS REST API "http://host:9870"
    spark_ping_timeout: float = 10.0           # 启动后 Spark 连通检查超时秒数（0=跳过）
    spark_ping_retries: int = 3               # 连通检查最大重试次数
    spark_ping_retry_delay: float = 60.0      # 重试间隔秒数（默认 60s）


class DataSection(BaseModel):
    """数据路径配置节"""
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    reports_dir: str = "data/reports"


class PipelineConfig(BaseModel):
    """单条流水线配置"""
    schedule: str = ""                         # cron 表达式，空字符串表示仅手动
    steps: list[str] = []                      # ["crawl", "clean_data"]
    step_failure: Literal["stop", "skip", "retry"] = "stop"
    max_retries: int = 0                       # 流水线级重试（仅 retry 模式）


class SchedulerConfig(BaseModel):
    """调度配置节"""
    pipelines: dict[str, PipelineConfig] = {}


class AppConfig(BaseModel):
    """应用根配置"""
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
    scheduler: SchedulerConfig = SchedulerConfig()
