# Spark 分析引擎设计

Date: 2026-06-17 | Status: approved

## 概述

实现 `SparkEngine` 补完双引擎架构，同时将 `PandasEngine.clean_data()` 从分批滑窗改为全量加载，两个引擎共享同一 `AnalysisEngine` ABC 接口和报告模型。

## 文件结构

```
新建: src/bilianalysis/engine/spark_engine.py    # SparkEngine
修改: src/bilianalysis/engine/pandas_engine.py    # clean_data() 全量化，删除 batch/ParquetWriter
修改: src/bilianalysis/engine/__init__.py         # 新增 create_engine() 工厂函数

复用: src/bilianalysis/engine/base.py             # ABC + 报告模型（不改）
```

## 核心差异对比

| | PandasEngine | SparkEngine |
|---|---|---|
| 数据加载 | `glob("raw/week_*.json")` → `pd.read_json` | `spark.read.json("raw/week_*.json")` |
| 缺失值 | `fillna(0)` / `fillna("")` | `df.na.fill(0).na.fill("")` |
| 去重 | `drop_duplicates("aid", keep="first")` | `dropDuplicates(["aid"])` |
| 类型转换 | `astype("int64")` / `astype("float64")` | `col().cast("bigint")` / `cast("double")` |
| 异常值 | 布尔 mask 过滤 | `filter(col("view") >= 0 & ...)` |
| Parquet 写 | `df.to_parquet(path)` 单文件 | `df.write.mode("overwrite").parquet(path)` |
| 统计关联 | `pd.merge` + 行位置对齐 | Spark JOIN + row_id 对齐 |
| 聚类 | sklearn KMeans + PCA → scatter_data | MLlib KMeans，scatter_data 留空 |
| 预测 | sklearn LinearRegression | MLlib LinearRegression |
| 会话 | 无状态（用完即弃） | `SparkSession` 实例，构造时创建 |

## PandasEngine.clean_data() 简化

```
clean_data()
├── 1. glob("raw/week_*.json") → 全量 pd.read_json → 合并
├── 2. _extract_tables() → 5 张 DataFrame
├── 3. _fill_missing() → 数值 0 / 文本 ""
├── 4. drop_duplicates(["aid"], keep="first") → 去重
├── 5. _convert_types() → 统一 dtype
├── 6. 非负值校验 → 异常标记
├── 7. to_parquet() → 写出 5 张表到 processed/
└── 8. return CleanReport
```

删除：`_batch_size`、滑动窗口循环、跨批 `seen_aids` set、`pyarrow.ParquetWriter`、分批追写逻辑。

批量加载改为全量：所有 week JSON 读入内存后一次性 `pd.concat` 合并，拆表/清洗/写出均为一次操作。

## SparkEngine 构造

```python
class SparkEngine(AnalysisEngine):
    def __init__(self, data_config: DataSection):
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)
        self._spark = (
            SparkSession.builder
            .appName("BiliAnalysis")
            .master("local[*]")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .getOrCreate()
        )
```

## SparkEngine.clean_data()

```
clean_data()
├── 1. spark.read.json(f"{raw_dir}/week_*.json") → 全量加载，自动 schema 推导
├── 2. _extract_tables() → 5 张 Spark DataFrame
│      每行分配一个 row_id（自增），用于后续 Creator/Category 关联
├── 3. _fill_missing() → df.na.fill(0).na.fill("")
├── 4. dropDuplicates(["aid"]) → 去重
│      同步去重：用 row_id 过滤 Creator/Category
├── 5. _convert_types() → cast("bigint") / cast("double")
├── 6. filter 非负值 → 异常标记
├── 7. df.write.mode("overwrite").parquet(path) → 5 张表
└── 8. return CleanReport
```

**row_id 生成（`_extract_tables` 中）：**

```python
from pyspark.sql.functions import monotonically_increasing_id

# 每张明细表（Video/Creator/Category/VideoStat）行与一个 row_id 绑定
# 后续 JOIN 用 row_id 而非位置
video_df = video_df.withColumn("row_id", monotonically_increasing_id())
creator_df = creator_df.withColumn("row_id", monotonically_increasing_id())
# ...
```

## SparkEngine.statistics()

| 步骤 | 实现 |
|------|------|
| 读表 | `spark.read.parquet(processed_dir / name)` × 5 |
| Video + VideoStat | `join(on="aid")` |
| + Creator | `join(on="row_id")` |
| + Category | `join(on="row_id")` |
| + Weekly | pubdate 区间匹配：`crossJoin` + `filter(col("pubdate").between("start_time", "end_time"))` |
| 聚合 | `groupBy("week_number").agg(avg(...), count(...))` 等 |
| 输出 | `toPandas()` → 构造 `StatReport` Pydantic 模型 |

## SparkEngine.clustering()

```python
def clustering(self) -> ClusterReport:
    # StandardScaler → KMeans(k=3) → silhouette
    # 不输出 scatter_data（留空 {}）
    ...
    return ClusterReport(
        clusters=ClusterResult(k=3, clusters=[...], ...),
        scatter_data={"labels": [], "x": [], "y": []},  # 留空
        ...
    )
```

## SparkEngine.prediction()

同 PandasEngine 逻辑：周聚合序列 → MLlib `LinearRegression` → `PredictionReport`。特征 `[week_number, video_count]`，target 为周均 `avg_view` / `avg_like`，预测未来 4 周。

## 引擎工厂（__init__.py）

```python
def create_engine(config: AppConfig) -> AnalysisEngine:
    if config.analysis.engine == "spark":
        from bilianalysis.engine.spark_engine import SparkEngine
        return SparkEngine(config.data)
    from bilianalysis.engine.pandas_engine import PandasEngine
    return PandasEngine(config.data)
```

## 依赖

- `pyspark` — 已在 `pyproject.toml` 的 `[project.optional-dependencies]` 中，切为正式依赖或保持 optional

## 不在范围内

- 不做 SparkEngine 的 scatter_data（留空）
- 不修改 `AnalysisEngine` ABC 接口
- 不修改已有报告模型
- 不修改 config/ 模块
