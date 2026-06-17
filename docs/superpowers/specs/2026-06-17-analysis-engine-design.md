# 分析引擎设计

Date: 2026-06-17 | Status: approved

## 概述

实现统一分析引擎层。采用抽象接口 + Pandas 引擎首版实现，分批加载 raw JSON 清洗后写出 5 张 Parquet 表，支持统计分析、KMeans 聚类、线性回归预测。

Spark 引擎接口预留，后续实现。

## 文件结构

```
新增:
├── src/bilianalysis/engine/
│   ├── __init__.py              # 公开 API
│   ├── base.py                  # AnalysisEngine 抽象基类 + 报告模型
│   └── pandas_engine.py         # PandasEngine 实现

复用:
├── src/bilianalysis/config/model.py   # DataSection (raw_dir/processed_dir/reports_dir)
```

## 抽象接口

```python
# base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class CleanReport(BaseModel):
    total_weeks: int
    total_videos: int
    duplicates_dropped: int
    missing_filled: int
    outliers_flagged: int
    duration_seconds: float

class AnalysisEngine(ABC):
    @abstractmethod
    async def clean_data(self) -> CleanReport:
        """分批加载 raw JSON → 清洗 → 写出 5 张 Parquet 表"""
        ...

    @abstractmethod
    def statistics(self) -> "StatReport": ...
    @abstractmethod
    def clustering(self) -> "ClusterReport": ...
    @abstractmethod
    def prediction(self) -> "PredictionReport": ...
```

首版 `statistics()`/`clustering()`/`prediction()` 在 PandasEngine 中完整实现。SparkEngine 后续各自实现对应方法。

## 数据模型（5 张表）

对应 `docs/dev/models_design.md`，从 raw JSON 拆出：

| 表名 | 字段 | 主键 |
|------|------|------|
| Weekly | number, subject, name, start_time, end_time | number |
| Video | aid, bvid, title, desc, duration, pubdate, cid, pic | aid |
| Creator | mid, name, face | mid |
| Category | tid, tname, tid_v2, tname_v2 | tid |
| VideoStat | aid, view, like, coin, favorite, share, reply, danmaku | aid |

- `Category.tid_v2` / `tname_v2` 来源：`videos[].rcmd_reason.tid_v2/tname_v2`
- `VideoStat` 的 aid 为外键关联 Video

## clean_data() 数据流

```
clean_data(batch_size=10)
│
├── 1. 扫描 raw_dir 所有 week_NNN.json，按 number 排序
├── 2. 分批 for batch in sliding_window(files, batch_size):
│   │
│   ├── 2.1 加载：读取 batch 内 JSON → 合并为单批 DataFrame
│   ├── 2.2 拆表：从嵌套 JSON 拆出 5 张 pandas DataFrame
│   ├── 2.3 缺失值处理：数值列 → 0，文本列 → ""，时间列 → NaT
│   ├── 2.4 去重：跨批次 seen_aids: set[int] 全局去重，按 aid 保留首次出现
│   ├── 2.5 类型转换：统一 int64/float64/datetime64[ns]/string
│   ├── 2.6 异常值检测：VideoStat 非负值校验（view≥0, like≥0 等）
│   └── 2.7 写出：pyarrow.parquet.ParquetWriter 分批追加到 processed/
│             processed/Weekly.parquet
│             processed/Video.parquet
│             processed/Creator.parquet
│             processed/Category.parquet
│             processed/VideoStat.parquet
│
└── 3. 返回 CleanReport
```

- **每批独立清洗**，不需要跨窗口参照
- **pyarrow ParquetWriter**：第一批创建 writer + schema，后续 batch 直接 `write_table` 追加，最后 `close`
- **不引入 fastparquet**，pyarrow 是 pandas 默认后端已安装
- **重复调用 clean_data()**：全量覆盖——先清掉 processed/ 下旧 Parquet 再重洗

## statistics() 接口

```python
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
    by_creator: list[CreatorStats]   # TOP10
    by_week: list[WeeklyTrend]
```

执行：从 processed/ 读 5 张 Parquet → 一次全量 pd.merge + groupby 聚合。

## clustering() 接口

```python
class ClusterGroup(BaseModel):
    label: int
    tag: str                    # "爆款视频" | "普通热门" | "潜力视频"
    count: int
    centroid: dict[str, float]
    avg_view: float
    avg_like: float
    avg_coin: float
    avg_favorite: float
    sample_ids: list[int]       # TOP20 aid

class ClusterResult(BaseModel):
    k: int
    clusters: list[ClusterGroup]
    silhouette_score: float
    feature_importance: dict[str, float]

class ClusterReport(BaseModel):
    clusters: ClusterResult
    scatter_data: dict          # {labels: [...], x: [...], y: [...]}
    duration_seconds: float
```

- 特征：`view, like, coin, favorite` 四维，StandardScaler 标准化
- KMeans(k=3)，标签映射：高播放高互动 → "爆款视频"，中播放中互动 → "普通热门"，低播放高互动率 → "潜力视频"
- 散点图：PCA(n=2) 降维到 2D 供 ECharts 直接渲染
- `feature_importance`：按各特征在聚类中心的方差贡献排序

## prediction() 接口

```python
class PredictionResult(BaseModel):
    model_type: str             # "linear_regression"
    target: str                 # "view" | "like"
    r2_score: float
    mae: float
    coefficients: dict[str, float]
    intercept: float
    fitted: list[dict]          # [{week_number, actual, predicted}]
    forecast: list[dict]        # 未来 4 周 [{week_number, predicted}]

class PredictionReport(BaseModel):
    view_predict: PredictionResult
    like_predict: PredictionResult
    duration_seconds: float
```

- 样本：以**周聚合数据**为样本（statistics 的 by_week 序列），非单条视频
- 特征：week_number + 历史交互指标
- 只做 LinearRegression，预测未来 4 周
- 输出区分 `fitted`（历史拟合值）和 `forecast`（未来预测值）

## PandasEngine 实现

```python
class PandasEngine(AnalysisEngine):
    def __init__(self, data_config: DataSection):
        self._batch_size = 10
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)

    async def clean_data(self) -> CleanReport:
        """分批加载 + 滑动窗口清洗，pyarrow ParquetWriter 追写"""
        ...

    def statistics(self) -> StatReport:
        """读 processed/ Parquet → pd.merge → groupby → StatReport"""
        ...

    def clustering(self) -> ClusterReport:
        """StandardScaler → KMeans(k=3) → PCA(n=2) → ClusterReport"""
        ...

    def prediction(self) -> PredictionReport:
        """周序列 → LinearRegression → PredictionReport"""
        ...
```

## 配置集成

已有 `DataSection` 提供路径：

```python
data_config = DataSection(
    raw_dir="data/raw",
    processed_dir="data/processed",
    reports_dir="data/reports",
)
engine = PandasEngine(data_config)
```

不修改 `AnalysisSection`，analysis 引擎切换字段（`engine: "pandas" | "spark"`）在调用侧使用工厂或直接构建。

## 依赖

- `pandas` — 已有
- `scikit-learn` — 新增：`uv add scikit-learn`
- `pyarrow` — pandas 已有（默认后端），不额外添加

## 不在范围内

- 不做 SparkEngine 实现（接口留空抛出 NotImplementedError）
- 不做 FastAPI 后端 / 前端
- 不迁移 storage.py 的 DATA_DIR（已由 DataSection 管理）
- 不做热加载 / 增量清洗（每次 clean_data() 全量覆盖）
