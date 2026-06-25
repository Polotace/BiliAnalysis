"""分析引擎抽象基类和报告模型。"""
from abc import ABC, abstractmethod
from pydantic import BaseModel


# ── clean_data ──

class CleanReport(BaseModel):
    """清洗阶段产出报告。"""
    total_weeks: int
    total_videos: int
    duplicates_dropped: int
    missing_filled: int
    outliers_flagged: int
    duration_seconds: float


# ── statistics ──

class OverallStats(BaseModel):
    total_videos: int
    total_creators: int
    avg_view: float
    avg_like: float
    avg_coin: float
    avg_favorite: float
    avg_share: float
    avg_danmaku: float
    avg_like_rate: float
    avg_coin_rate: float
    avg_favorite_rate: float


class CategoryStats(BaseModel):
    tname: str
    video_count: int
    avg_view: float
    avg_like: float
    avg_interaction_rate: float


class CreatorStats(BaseModel):
    mid: int
    name: str
    appearance_count: int
    total_view: int
    total_like: int
    total_favorite: int


class WeeklyTrend(BaseModel):
    week_number: int
    video_count: int
    avg_view: float
    avg_like: float
    avg_interaction_rate: float


class StatReport(BaseModel):
    overall: OverallStats
    by_category: list[CategoryStats]
    by_creator: list[CreatorStats]
    by_week: list[WeeklyTrend]


# ── clustering ──

class ClusterGroup(BaseModel):
    label: int
    tag: str
    count: int
    centroid: dict[str, float]
    avg_view: float
    avg_like: float
    avg_coin: float
    avg_favorite: float
    sample_ids: list[int]


class ClusterResult(BaseModel):
    k: int
    clusters: list[ClusterGroup]
    silhouette_score: float
    feature_importance: dict[str, float]


class ClusterReport(BaseModel):
    clusters: ClusterResult
    scatter_data: dict
    duration_seconds: float


# ── prediction ──

class PredictionResult(BaseModel):
    model_type: str
    target: str
    r2_score: float
    mae: float
    rmse: float = 0.0
    test_r2_score: float | None = None
    test_rmse: float | None = None
    train_size: int = 0
    test_size: int = 0
    coefficients: dict[str, float]
    intercept: float
    fitted: list[dict]
    forecast: list[dict]


class PredictionReport(BaseModel):
    view_predict: PredictionResult
    like_predict: PredictionResult
    duration_seconds: float


# ── model_comparison ──

class SingleModelResult(BaseModel):
    """单个回归模型的交叉验证结果。"""
    model_name: str
    r2_mean: float
    r2_std: float
    mae_mean: float
    mae_std: float
    rmse_mean: float
    rmse_std: float
    train_time_seconds: float


class FeatureImportanceItem(BaseModel):
    """单个特征的重要性。"""
    feature: str
    importance: float


class ModelComparisonReport(BaseModel):
    """多模型回归对比报告 — 视频级预测。"""
    n_samples: int
    n_features: int
    n_nlp_features: int = 0
    target: str
    models: list[SingleModelResult]
    best_model: str
    feature_importance: list[FeatureImportanceItem]
    predicted_vs_actual: list[dict]
    bayesian_opt: dict | None = None
    duration_seconds: float


# ── ABC ──

class AnalysisEngine(ABC):
    @abstractmethod
    async def clean_data(self) -> CleanReport:
        """分批加载 raw JSON → 清洗 → 写出 5 张 Parquet 表。"""
        ...

    @abstractmethod
    def statistics(self) -> StatReport:
        """从 processed/ Parquet 读取 → join → groupby 聚合。"""
        ...

    @abstractmethod
    def clustering(self) -> ClusterReport:
        """从 processed/ Parquet 读取 → KMeans(k=3) 聚类 → PCA 降维。"""
        ...

    @abstractmethod
    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet 读取 → 周序列 LinearRegression 预测。"""
        ...

    @abstractmethod
    def model_comparison(self) -> ModelComparisonReport:
        """加载 raw JSON → 特征工程 → 训练 5 个回归模型 (5-fold CV) → 模型对比报告。"""
        ...
