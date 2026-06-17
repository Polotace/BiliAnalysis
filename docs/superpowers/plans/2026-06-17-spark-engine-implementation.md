# Spark 引擎实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 SparkEngine 补完双引擎架构；同时将 PandasEngine.clean_data() 从分批滑窗简化为全量加载。

**Architecture:** 简化 PandasEngine → 创建 SparkEngine（4 方法：spark.read.json 全量加载 + row_id 关联 + MLlib 聚类/预测）→ `__init__.py` 添加工厂函数 `create_engine(config)`。

**Tech Stack:** PySpark 4.1.2（已安装）, pyspark.ml.clustering/pyspark.ml.regression

---

### Task 1: Simplify PandasEngine.clean_data() — Full Load

**Files:**
- Modify: `src/bilianalysis/engine/pandas_engine.py`

- [ ] **Step 1: Read current file and apply edits**

Modify `src/bilianalysis/engine/pandas_engine.py`:

**Edit 1**: Remove imports (lines 8-9):

```python
# DELETE these two lines:
import pyarrow as pa
import pyarrow.parquet as pq
```

**Edit 2**: Change `__init__` — remove `batch_size`:

```python
# OLD (lines 33-37):
    def __init__(self, data_config: DataSection, batch_size: int = 10):
        self._batch_size = batch_size
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)

# NEW:
    def __init__(self, data_config: DataSection):
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)
```

**Edit 3**: Update docstring (line 27-31):

```python
# OLD:
    """基于 Pandas 的分析引擎。

    分批加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """

# NEW:
    """基于 Pandas 的分析引擎。

    全量加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """
```

**Edit 4**: Replace the ENTIRE `clean_data()` method (lines 41-154) with:

```python
    async def clean_data(self) -> CleanReport:
        start_time = time.monotonic()

        # 1. 全量加载所有 week JSON
        files = sorted(self._raw_dir.glob("week_*.json"),
                       key=lambda p: int(p.stem.split("_")[1]))
        records = []
        for fp in files:
            with open(fp, encoding="utf-8") as fh:
                records.append(json.load(fh))

        # 2. 拆表
        dfs = self._extract_tables(records)

        # 3. 缺失值
        na_before = sum(df.isna().sum().sum() for df in dfs.values())
        dfs = self._fill_missing(dfs)
        missing_filled = na_before

        # 4. 去重（按 aid，保留首次出现）
        video_df = dfs["Video"]
        before = len(video_df)
        if not video_df.empty:
            keep_mask = ~video_df["aid"].duplicated(keep="first")
            video_df = video_df[keep_mask].reset_index(drop=True)
            duplicates_dropped = before - len(video_df)
            dfs["Video"] = video_df
            # 同步关联表
            dfs["VideoStat"] = dfs["VideoStat"].loc[keep_mask.values].reset_index(drop=True) if not dfs["VideoStat"].empty else dfs["VideoStat"]
            dfs["Creator"] = dfs["Creator"].loc[keep_mask.values].reset_index(drop=True) if not dfs["Creator"].empty else dfs["Creator"]
            dfs["Category"] = dfs["Category"].loc[keep_mask.values].reset_index(drop=True) if not dfs["Category"].empty else dfs["Category"]
        else:
            duplicates_dropped = 0

        # 5. 类型转换
        dfs = self._convert_types(dfs)

        # 6. 异常值检测
        stat_df = dfs["VideoStat"]
        outliers_flagged = 0
        if not stat_df.empty:
            stat_before = len(stat_df)
            valid = (
                (stat_df["view"] >= 0) & (stat_df["like"] >= 0) &
                (stat_df["coin"] >= 0) & (stat_df["favorite"] >= 0) &
                (stat_df["share"] >= 0) & (stat_df["reply"] >= 0) &
                (stat_df["danmaku"] >= 0)
            )
            dfs["VideoStat"] = stat_df[valid].reset_index(drop=True)
            if not valid.all():
                dfs["Video"] = dfs["Video"].loc[valid.values].reset_index(drop=True)
                dfs["Creator"] = dfs["Creator"].loc[valid.values].reset_index(drop=True)
                dfs["Category"] = dfs["Category"].loc[valid.values].reset_index(drop=True)
            outliers_flagged = stat_before - len(dfs["VideoStat"])

        # 7. 写出 Parquet
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        for f in self._processed_dir.glob("*.parquet"):
            f.unlink()
        for table_name, df in dfs.items():
            if not df.empty:
                df.to_parquet(self._processed_dir / f"{table_name}.parquet", index=False)

        total_videos = len(dfs["Video"])
        total_weeks = len(files)
        duration = time.monotonic() - start_time
        return CleanReport(
            total_weeks=total_weeks, total_videos=total_videos,
            duplicates_dropped=duplicates_dropped, missing_filled=missing_filled,
            outliers_flagged=outliers_flagged, duration_seconds=round(duration, 2),
        )
```

- [ ] **Step 2: Run existing engine tests — some should still pass**

Run: `uv run pytest tests/test_engine.py -v -k "not sliding_window" 2>&1`
Expected: Most tests pass except tests that use `batch_size` argument

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/engine/pandas_engine.py
git commit -m "refactor: simplify PandasEngine.clean_data() to full-load strategy"
```

---

### Task 2: Update test_engine.py for Simplified PandasEngine

**Files:**
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Update tests to remove batch_size references**

**Edit 1**: Remove `batch_size=5` from `test_clean_data_basic` (line 148):

```python
# OLD:
        engine = PandasEngine(data_conf, batch_size=5)
# NEW:
        engine = PandasEngine(data_conf)
```

**Edit 2**: Replace the sliding window test with a renamed version (lines 162-180):

```python
    @pytest.mark.asyncio
    async def test_clean_data_full_load(self, tmp_path, monkeypatch):
        """3 个 week，全量加载一次处理。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        for n in [1, 2, 3]:
            data = _make_week_json(n, [_make_video(n * 100)])
            (raw_dir / f"week_{n:03d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = await engine.clean_data()

        assert report.total_weeks == 3
        assert report.total_videos == 3
        df = pd.read_parquet(processed_dir / "Video.parquet")
        assert len(df) == 3
```

**Edit 3**: Remove `batch_size=10` from `test_clean_data_missing_values` (line 197):

```python
# OLD:
        engine = PandasEngine(data_conf, batch_size=10)
# NEW:
        engine = PandasEngine(data_conf)
```

**Edit 4**: Update dedup test (lines 206-225): remove `batch_size=2`:

```python
        engine = PandasEngine(data_conf)
```

**Edit 5**: Remove `batch_size=10` from `test_clean_data_outliers` (line 239):

```python
        engine = PandasEngine(data_conf)
```

**Edit 6**: Remove `batch_size=10` from `test_clean_data_type_conversion` (line 255):

```python
        engine = PandasEngine(data_conf)
```

- [ ] **Step 2: Run engine tests**

Run: `uv run pytest tests/test_engine.py -v`
Expected: 22 PASS (all adapted)

- [ ] **Step 3: Commit**

```bash
git add tests/test_engine.py
git commit -m "test: adapt PandasEngine tests for full-load strategy"
```

---

### Task 3: Create SparkEngine — Structure + clean_data()

**Files:**
- Create: `src/bilianalysis/engine/spark_engine.py`

- [ ] **Step 1: Create spark_engine.py**

Create `src/bilianalysis/engine/spark_engine.py`:

```python
"""Spark 分析引擎实现。"""
import time
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, monotonically_increasing_id, avg, count, sum as spark_sum, when, lit
from pyspark.sql.types import LongType, DoubleType, StringType

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


class SparkEngine(AnalysisEngine):
    """基于 PySpark 的分析引擎。

    全量加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """

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
            .config("spark.driver.bindAddress", "127.0.0.1")
            .getOrCreate()
        )

    # ── clean_data ───────────────────────────────────────────

    def clean_data(self) -> CleanReport:
        """全量加载 raw JSON → 清洗 → 写出 5 张 Parquet。"""
        start_time = time.monotonic()

        # 1. 全量加载 week_*.json（spark.read.json 自动 schema 推导）
        raw_pattern = str(self._raw_dir / "week_*.json")
        raw_df = self._spark.read.json(raw_pattern)

        total_weeks = raw_df.count()

        # 2. 拆表 + row_id
        dfs = self._extract_tables(raw_df)

        # 3. 缺失值
        dfs = self._fill_missing(dfs)

        # 4. 去重（按 aid）
        video_df = dfs["Video"]
        before = video_df.count()
        video_df = video_df.dropDuplicates(["aid"])
        duplicates_dropped = before - video_df.count()
        dfs["Video"] = video_df
        # 同步关联表
        kept_ids = video_df.select("row_id")
        dfs["VideoStat"] = dfs["VideoStat"].join(kept_ids, "row_id", "inner")
        dfs["Creator"] = dfs["Creator"].join(kept_ids, "row_id", "inner")
        dfs["Category"] = dfs["Category"].join(kept_ids, "row_id", "inner")

        # 5. 类型转换
        dfs = self._convert_types(dfs)

        # 6. 异常值检测
        stat_df = dfs["VideoStat"]
        stat_before = stat_df.count()
        valid = (
            (col("view") >= 0) & (col("like") >= 0) & (col("coin") >= 0) &
            (col("favorite") >= 0) & (col("share") >= 0) & (col("reply") >= 0) &
            (col("danmaku") >= 0)
        )
        dfs["VideoStat"] = stat_df.filter(valid)
        outliers_flagged = stat_before - dfs["VideoStat"].count()
        # 同步关联表
        valid_ids = dfs["VideoStat"].select("row_id")
        dfs["Video"] = dfs["Video"].join(valid_ids, "row_id", "inner")
        dfs["Creator"] = dfs["Creator"].join(valid_ids, "row_id", "inner")
        dfs["Category"] = dfs["Category"].join(valid_ids, "row_id", "inner")

        # 7. 写出 Parquet（全量覆盖）
        for table_name, df in dfs.items():
            out_path = str(self._processed_dir / table_name)
            df.write.mode("overwrite").parquet(out_path)

        total_videos = dfs["Video"].count()
        duration = time.monotonic() - start_time
        return CleanReport(
            total_weeks=total_weeks, total_videos=total_videos,
            duplicates_dropped=duplicates_dropped, missing_filled=0,
            outliers_flagged=outliers_flagged, duration_seconds=round(duration, 2),
        )

    # ── 清洗子步骤 ──────────────────────────────────────────

    def _extract_tables(self, raw_df: DataFrame) -> dict[str, DataFrame]:
        """从 raw Spark DataFrame 拆出 5 张表，每行带 row_id 用于关联。"""
        # Weekly
        weekly = raw_df.select(
            col("number"),
            col("config.subject").alias("subject"),
            col("config.name").alias("name"),
            col("config.start_time").alias("start_time"),
            col("config.end_time").alias("end_time"),
        )

        # Videos — explode videos 数组，每行一个视频
        video_exploded = raw_df.withColumn("video", col("videos").getItem(0))
        # 实际需要 explode: selectExpr("inline(videos)")
        from pyspark.sql.functions import explode
        video_rows = raw_df.select(
            col("number").alias("week_number"),
            explode("videos").alias("v")
        )
        video = video_rows.select(
            col("v.aid").alias("aid"),
            col("v.bvid").alias("bvid"),
            col("v.title").alias("title"),
            col("v.desc").alias("desc"),
            col("v.duration").alias("duration"),
            col("v.pubdate").alias("pubdate"),
            col("v.cid").alias("cid"),
            col("v.pic").alias("pic"),
            monotonically_increasing_id().alias("row_id"),
        )

        creator = video_rows.select(
            col("v.owner.mid").alias("mid"),
            col("v.owner.name").alias("name"),
            col("v.owner.face").alias("face"),
            monotonically_increasing_id().alias("row_id"),
        )

        category = video_rows.select(
            col("v.tid").alias("tid"),
            col("v.tname").alias("tname"),
            col("v.rcmd_reason.tid_v2").alias("tid_v2"),
            col("v.rcmd_reason.tname_v2").alias("tname_v2"),
            monotonically_increasing_id().alias("row_id"),
        )

        stat = video_rows.select(
            col("v.stat.aid").alias("aid"),
            col("v.stat.view").alias("view"),
            col("v.stat.like").alias("like"),
            col("v.stat.coin").alias("coin"),
            col("v.stat.favorite").alias("favorite"),
            col("v.stat.share").alias("share"),
            col("v.stat.reply").alias("reply"),
            col("v.stat.danmaku").alias("danmaku"),
            monotonically_increasing_id().alias("row_id"),
        )

        return {
            "Weekly": weekly,
            "Video": video,
            "Creator": creator,
            "Category": category,
            "VideoStat": stat,
        }

    def _fill_missing(self, dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
        """缺失值填充：数值 → 0，字符串 → ""。"""
        numeric_defaults = {
            "Weekly": {"start_time": 0, "end_time": 0},
            "Video": {"aid": 0, "duration": 0, "cid": 0, "pubdate": 0},
            "Creator": {"mid": 0},
            "Category": {"tid": 0, "tid_v2": 0},
            "VideoStat": {"aid": 0, "view": 0, "like": 0, "coin": 0, "favorite": 0, "share": 0, "reply": 0, "danmaku": 0},
        }
        for name, df in dfs.items():
            defaults = numeric_defaults.get(name, {})
            fill_map = {k: v for k, v in defaults.items() if k in df.columns}
            if fill_map:
                df = df.na.fill(fill_map)
            # 字符串列填充 ""
            string_cols = [c for c, t in df.dtypes if t == "string"]
            if string_cols:
                df = df.na.fill("").fill("", subset=string_cols)
            dfs[name] = df
        return dfs

    def _convert_types(self, dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
        """统一各表列类型。"""
        # VideoStat: 数值 → double
        for col_name in ["view", "like", "coin", "favorite", "share", "reply", "danmaku"]:
            if col_name in dfs["VideoStat"].columns:
                dfs["VideoStat"] = dfs["VideoStat"].withColumn(col_name, col(col_name).cast(DoubleType()))
        for col_name in ["aid"]:
            if col_name in dfs["VideoStat"].columns:
                dfs["VideoStat"] = dfs["VideoStat"].withColumn(col_name, col(col_name).cast(LongType()))

        # Video
        for col_name in ["aid", "duration", "cid", "pubdate"]:
            if col_name in dfs["Video"].columns:
                dfs["Video"] = dfs["Video"].withColumn(col_name, col(col_name).cast(LongType()))

        # Creator
        if "mid" in dfs["Creator"].columns:
            dfs["Creator"] = dfs["Creator"].withColumn("mid", col("mid").cast(LongType()))

        # Category
        for col_name in ["tid", "tid_v2"]:
            if col_name in dfs["Category"].columns:
                dfs["Category"] = dfs["Category"].withColumn(col_name, col(col_name).cast(LongType()))

        # Weekly
        if "number" in dfs["Weekly"].columns:
            dfs["Weekly"] = dfs["Weekly"].withColumn("number", col("number").cast(LongType()))

        return dfs

    # ── statistics ───────────────────────────────────────────

    def statistics(self) -> StatReport:
        raise NotImplementedError("statistics: to be implemented in Task 4")

    # ── clustering ───────────────────────────────────────────

    def clustering(self) -> ClusterReport:
        raise NotImplementedError("clustering: to be implemented in Task 5")

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        raise NotImplementedError("prediction: to be implemented in Task 6")
```

- [ ] **Step 2: Verify clean_data() runs**

Run: `uv run python -c "
from bilianalysis.config import DataSection
from bilianalysis.engine.spark_engine import SparkEngine
import json, tempfile, os

td = tempfile.mkdtemp()
raw = os.path.join(td, 'raw')
processed = os.path.join(td, 'processed')
os.makedirs(raw)

data = {'number': 1, 'config': {'subject': 'test', 'name': 'test', 'start_time': 1600000000, 'end_time': 1600600000}, 'videos': [
    {'aid': 1, 'bvid': 'BV1', 'title': 'test', 'desc': '', 'duration': 120,
     'pubdate': 1600000000, 'cid': 10, 'pic': '',
     'owner': {'mid': 100, 'name': 'UP', 'face': ''},
     'stat': {'aid': 1, 'view': 1000, 'like': 50, 'coin': 10, 'favorite': 20, 'share': 5, 'reply': 8, 'danmaku': 12},
     'tid': 1, 'tname': '动画'}
]}
with open(os.path.join(raw, 'week_001.json'), 'w') as f:
    json.dump(data, f)

engine = SparkEngine(DataSection(raw_dir=raw, processed_dir=processed))
report = engine.clean_data()
print(f'Cleaned: {report.total_weeks} weeks, {report.total_videos} videos')
engine._spark.stop()
import shutil; shutil.rmtree(td, ignore_errors=True)
"
```
Expected: `Cleaned: 1 weeks, 1 videos`

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/engine/spark_engine.py
git commit -m "feat: add SparkEngine with clean_data()"
```

---

### Task 4: Implement SparkEngine.statistics()

**Files:**
- Modify: `src/bilianalysis/engine/spark_engine.py` (replace statistics() stub)

- [ ] **Step 1: Read current spark_engine.py then replace statistics() stub**

Replace the `statistics()` stub with:

```python
    def statistics(self) -> StatReport:
        """从 processed/ Parquet 读取 → JOIN → groupBy 聚合 → StatReport。"""
        # 1. 读取 5 张 Parquet
        weekly = self._spark.read.parquet(str(self._processed_dir / "Weekly"))
        video = self._spark.read.parquet(str(self._processed_dir / "Video"))
        stat = self._spark.read.parquet(str(self._processed_dir / "VideoStat"))
        creator = self._spark.read.parquet(str(self._processed_dir / "Creator"))
        category = self._spark.read.parquet(str(self._processed_dir / "Category"))

        # 2. Join: Video + VideoStat on aid; + Creator/Category on row_id
        df = video.join(stat, "aid", "inner")
        df = df.join(creator, "row_id", "left")
        df = df.join(category, "row_id", "left")

        # 3. 周匹配
        df = df.crossJoin(weekly.withColumnRenamed("start_time", "w_start")
                           .withColumnRenamed("end_time", "w_end")
                           .withColumnRenamed("number", "week_number"))
        df = df.filter((col("pubdate") >= col("w_start")) & (col("pubdate") <= col("w_end")))

        # 4. 交互率
        df = df.withColumn("like_rate", col("like") / when(col("view") == 0, 1).otherwise(col("view")))
        df = df.withColumn("coin_rate", col("coin") / when(col("view") == 0, 1).otherwise(col("view")))
        df = df.withColumn("favorite_rate", col("favorite") / when(col("view") == 0, 1).otherwise(col("view")))

        # 5. OverallStats
        overall_row = df.agg(
            count("aid").alias("total_videos"),
            count("mid").alias("total_creators"),
            avg("view"), avg("like"), avg("coin"), avg("favorite"),
            avg("share"), avg("danmaku"),
            avg("like_rate"), avg("coin_rate"), avg("favorite_rate"),
        ).collect()[0]
        overall = OverallStats(
            total_videos=int(overall_row["total_videos"]),
            total_creators=int(overall_row["total_creators"]),
            avg_view=round(float(overall_row["avg(view)"]), 2),
            avg_like=round(float(overall_row["avg(like)"]), 2),
            avg_coin=round(float(overall_row["avg(coin)"]), 2),
            avg_favorite=round(float(overall_row["avg(favorite)"]), 2),
            avg_share=round(float(overall_row["avg(share)"]), 2),
            avg_danmaku=round(float(overall_row["avg(danmaku)"]), 2),
            avg_like_rate=round(float(overall_row["avg(like_rate)"]), 4),
            avg_coin_rate=round(float(overall_row["avg(coin_rate)"]), 4),
            avg_favorite_rate=round(float(overall_row["avg(favorite_rate)"]), 4),
        )

        # 6. by_category
        cat_rows = df.groupBy("tname").agg(
            count("aid").alias("video_count"),
            avg("view"), avg("like"), avg("like_rate").alias("avg_interaction_rate"),
        ).collect()
        by_category = [CategoryStats(
            tname=r["tname"], video_count=int(r["video_count"]),
            avg_view=round(float(r["avg(view)"]), 2),
            avg_like=round(float(r["avg(like)"]), 2),
            avg_interaction_rate=round(float(r["avg_interaction_rate"]), 4),
        ) for r in cat_rows]

        # 7. by_creator (TOP10)
        creator_rows = df.groupBy("mid", "name").agg(
            count("aid").alias("appearance_count"),
            spark_sum("view").alias("total_view"),
            spark_sum("like").alias("total_like"),
            spark_sum("favorite").alias("total_favorite"),
        ).orderBy(col("appearance_count").desc()).limit(10).collect()
        by_creator = [CreatorStats(
            mid=int(r["mid"]), name=r["name"],
            appearance_count=int(r["appearance_count"]),
            total_view=int(r["total_view"]),
            total_like=int(r["total_like"]),
            total_favorite=int(r["total_favorite"]),
        ) for r in creator_rows]

        # 8. by_week
        week_rows = df.groupBy("week_number").agg(
            count("aid").alias("video_count"),
            avg("view"), avg("like"), avg("like_rate").alias("avg_interaction_rate"),
        ).orderBy("week_number").collect()
        by_week = [WeeklyTrend(
            week_number=int(r["week_number"]),
            video_count=int(r["video_count"]),
            avg_view=round(float(r["avg(view)"]), 2),
            avg_like=round(float(r["avg(like)"]), 2),
            avg_interaction_rate=round(float(r["avg(like_rate)"]), 4),
        ) for r in week_rows]

        return StatReport(overall=overall, by_category=by_category, by_creator=by_creator, by_week=by_week)
```

- [ ] **Step 2: Smoke test statistics via clean_data then statistics**

Run:
```bash
uv run python -c "
from bilianalysis.config import DataSection
from bilianalysis.engine.spark_engine import SparkEngine
import json, tempfile, os, shutil

td = tempfile.mkdtemp()
raw = os.path.join(td, 'raw')
processed = os.path.join(td, 'processed')
os.makedirs(raw)

for n in [1, 2]:
    data = {'number': n, 'config': {'subject': f'第{n}期', 'name': f'test', 'start_time': 1600000000 + (n-1)*604800, 'end_time': 1600000000 + n*604800}, 'videos': [
        {'aid': n*100 + i, 'bvid': f'BV{n}{i}', 'title': f'v{n}{i}', 'desc': '', 'duration': 120,
         'pubdate': 1600000000 + (n-1)*604800, 'cid': n*10 + i, 'pic': '',
         'owner': {'mid': n*1000 + i, 'name': f'UP{n}{i}', 'face': ''},
         'stat': {'aid': n*100 + i, 'view': 10000 + n*5000, 'like': 500 + n*200, 'coin': 100, 'favorite': 200, 'share': 30, 'reply': 50, 'danmaku': 60},
         'tid': n, 'tname': '动画' if n == 1 else '游戏'}
        for i in range(3)
    ]}
    with open(os.path.join(raw, f'week_{n:03d}.json'), 'w') as f:
        json.dump(data, f, ensure_ascii=False)

engine = SparkEngine(DataSection(raw_dir=raw, processed_dir=processed))
report = engine.clean_data()
print(f'Cleaned: {report.total_weeks} weeks, {report.total_videos} videos')

stats = engine.statistics()
print(f'Stats: {stats.overall.total_videos} videos, avg_view={stats.overall.avg_view}')
print(f'Categories: {len(stats.by_category)}, Creators: {len(stats.by_creator)}, Weeks: {len(stats.by_week)}')

engine._spark.stop()
shutil.rmtree(td, ignore_errors=True)
"
```
Expected: cleanup succeeds, statistics prints meaningful numbers

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/engine/spark_engine.py
git commit -m "feat: implement SparkEngine.statistics()"
```

---

### Task 5: Implement SparkEngine.clustering() + prediction()

**Files:**
- Modify: `src/bilianalysis/engine/spark_engine.py` (replace both stubs)

- [ ] **Step 1: Add MLlib imports**

Add at top of spark_engine.py after existing imports:

```python
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.clustering import KMeans as SparkKMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.regression import LinearRegression as SparkLinearRegression
```

- [ ] **Step 2: Replace clustering() stub**

```python
    def clustering(self) -> ClusterReport:
        """从 processed/ Stat 读取 → KMeans(k=3) → ClusterReport（scatter_data 留空）。"""
        start_time = time.monotonic()
        stat = self._spark.read.parquet(str(self._processed_dir / "VideoStat"))

        total = stat.count()
        if total < 3:
            duration = time.monotonic() - start_time
            return ClusterReport(
                clusters=ClusterResult(k=3, clusters=[], silhouette_score=0.0, feature_importance={}),
                scatter_data={"labels": [], "x": [], "y": []},
                duration_seconds=round(duration, 2),
            )

        features = ["view", "like", "coin", "favorite"]
        assembler = VectorAssembler(inputCols=features, outputCol="features")
        assembled = assembler.transform(stat)

        scaler = StandardScaler(inputCol="features", outputCol="scaled_features",
                                withStd=True, withMean=True)
        scaler_model = scaler.fit(assembled)
        scaled = scaler_model.transform(assembled)

        kmeans = SparkKMeans(k=3, seed=42, featuresCol="scaled_features", predictionCol="label")
        model = kmeans.fit(scaled)
        predictions = model.transform(scaled)

        evaluator = ClusteringEvaluator(featuresCol="scaled_features", metricName="silhouette")
        sil_score = evaluator.evaluate(predictions)

        # 聚类中心
        centers = model.clusterCenters()
        import pandas as pd
        centers_df = pd.DataFrame([c.tolist() for c in centers], columns=features)
        importance = {f: round(float(centers_df[f].var()), 4) for f in features}

        # 聚合每个 cluster
        stat_pd = stat.toPandas()
        labels_pd = predictions.select("aid", "label").toPandas()
        merged = stat_pd.merge(labels_pd, on="aid")
        merged["interaction_rate"] = (merged["like"] + merged["coin"] + merged["favorite"]) / merged["view"].replace(0, 1)

        label_view_rank = {}
        for label_idx in range(3):
            mask = merged["label"] == label_idx
            label_view_rank[label_idx] = float(merged.loc[mask, "view"].mean()) if mask.any() else 0.0

        sorted_labels = sorted(label_view_rank, key=label_view_rank.get, reverse=True)
        tag_map = {sorted_labels[0]: "爆款视频", sorted_labels[1]: "普通热门", sorted_labels[2]: "潜力视频"}

        clusters = []
        for label_idx in range(3):
            mask = merged["label"] == label_idx
            cluster_data = merged[mask]
            centroid = {f: round(float(cluster_data[f].mean()), 2) for f in features}
            sample_ids = cluster_data["aid"].head(20).astype(int).tolist()
            clusters.append(ClusterGroup(
                label=label_idx, tag=tag_map[label_idx], count=int(mask.sum()),
                centroid=centroid,
                avg_view=round(float(cluster_data["view"].mean()), 2),
                avg_like=round(float(cluster_data["like"].mean()), 2),
                avg_coin=round(float(cluster_data["coin"].mean()), 2),
                avg_favorite=round(float(cluster_data["favorite"].mean()), 2),
                sample_ids=sample_ids,
            ))

        duration = time.monotonic() - start_time
        return ClusterReport(
            clusters=ClusterResult(k=3, clusters=clusters,
                                   silhouette_score=round(float(sil_score), 4),
                                   feature_importance=importance),
            scatter_data={"labels": [], "x": [], "y": []},
            duration_seconds=round(duration, 2),
        )
```

- [ ] **Step 3: Replace prediction() stub**

```python
    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet → 周聚合 → LinearRegression → PredictionReport。"""
        start_time = time.monotonic()
        video = self._spark.read.parquet(str(self._processed_dir / "Video"))
        stat = self._spark.read.parquet(str(self._processed_dir / "VideoStat"))
        weekly = self._spark.read.parquet(str(self._processed_dir / "Weekly"))

        merged = video.join(stat, "aid", "inner")
        merged = merged.crossJoin(weekly.withColumnRenamed("start_time", "w_start")
                                   .withColumnRenamed("end_time", "w_end")
                                   .withColumnRenamed("number", "week_number"))
        merged = merged.filter((col("pubdate") >= col("w_start")) & (col("pubdate") <= col("w_end")))

        weekly_agg = merged.groupBy("week_number").agg(
            avg("view").alias("avg_view"), avg("like").alias("avg_like"),
            avg("coin").alias("avg_coin"), avg("favorite").alias("avg_favorite"),
            count("aid").alias("video_count"),
        ).orderBy("week_number")

        df = weekly_agg.toPandas()
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score, mean_absolute_error

        def _predict(target: str) -> PredictionResult:
            if len(df) < 3:
                return PredictionResult(
                    model_type="linear_regression", target=target, r2_score=0.0, mae=0.0,
                    coefficients={}, intercept=0.0, fitted=[], forecast=[],
                )
            feature_cols = ["week_number", "video_count"]
            X = df[feature_cols].values
            y = df[f"avg_{target}"].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)

            r2 = r2_score(y, y_pred)
            mae = mean_absolute_error(y, y_pred)
            coef = {feature_cols[i]: round(float(model.coef_[i]), 4) for i in range(len(feature_cols))}
            intercept = round(float(model.intercept_), 2)

            fitted = [
                {"week_number": int(df.iloc[i]["week_number"]),
                 "actual": round(float(y[i]), 2),
                 "predicted": round(float(y_pred[i]), 2)}
                for i in range(len(df))
            ]
            last_week = int(df["week_number"].max())
            avg_vc = int(df["video_count"].mean())
            future_X = np.array([[last_week + i, avg_vc] for i in range(1, 5)])
            future_pred = model.predict(future_X)
            forecast = [
                {"week_number": int(last_week + i), "predicted": round(float(future_pred[j]), 2)}
                for j, i in enumerate(range(1, 5))
            ]
            return PredictionResult(
                model_type="linear_regression", target=target,
                r2_score=round(float(r2), 4), mae=round(float(mae), 2),
                coefficients=coef, intercept=intercept,
                fitted=fitted, forecast=forecast,
            )

        view_result = _predict("view")
        like_result = _predict("like")
        duration = time.monotonic() - start_time
        return PredictionReport(
            view_predict=view_result, like_predict=like_result,
            duration_seconds=round(duration, 2),
        )
```

- [ ] **Step 4: Smoke test all 4 methods**

Run:
```bash
uv run python -c "
from bilianalysis.config import DataSection
from bilianalysis.engine.spark_engine import SparkEngine
import json, tempfile, os, shutil

td = tempfile.mkdtemp()
raw = os.path.join(td, 'raw')
processed = os.path.join(td, 'processed')
os.makedirs(raw)

import numpy as np; np.random.seed(42)
for n in range(1, 8):
    base_view = 10000 + n * 2000
    data = {'number': n, 'config': {'subject': f'第{n}期', 'name': f'test', 'start_time': 1600000000 + (n-1)*604800, 'end_time': 1600000000 + n*604800}, 'videos': [
        {'aid': n*100 + i, 'bvid': f'BV{n}{i}', 'title': f'v{n}{i}', 'desc': '', 'duration': 120,
         'pubdate': 1600000000 + (n-1)*604800 + i*1000, 'cid': n*10 + i, 'pic': '',
         'owner': {'mid': n*1000 + i, 'name': f'UP{n}{i}', 'face': ''},
         'stat': {'aid': n*100 + i, 'view': max(0, base_view + np.random.randint(-1000, 1000)),
                  'like': max(0, base_view//20 + np.random.randint(-20, 20)),
                  'coin': 100, 'favorite': 200, 'share': 30, 'reply': 50, 'danmaku': 60},
         'tid': 1, 'tname': '动画'}
        for i in range(20)
    ]}
    with open(os.path.join(raw, f'week_{n:03d}.json'), 'w') as f:
        json.dump(data, f, ensure_ascii=False)

engine = SparkEngine(DataSection(raw_dir=raw, processed_dir=processed))
cr = engine.clean_data()
print(f'Clean: {cr.total_weeks}w {cr.total_videos}v')

sr = engine.statistics()
print(f'Stats: {sr.overall.total_videos}v avg_view={sr.overall.avg_view} {len(sr.by_category)}cats {len(sr.by_creator)}creators {len(sr.by_week)}wks')

cl = engine.clustering()
print(f'Cluster: k={cl.clusters.k} sil={cl.clusters.silhouette_score} scatter_data_empty={not cl.scatter_data[\"x\"]}')

pr = engine.prediction()
print(f'Predict: view_r2={pr.view_predict.r2_score} like_r2={pr.like_predict.r2_score} forecast={len(pr.view_predict.forecast)}wks')

engine._spark.stop()
shutil.rmtree(td, ignore_errors=True)
"
```
Expected: all 4 methods succeed with meaningful output

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/engine/spark_engine.py
git commit -m "feat: implement SparkEngine.clustering() and prediction()"
```

---

### Task 6: Add create_engine() Factory + Final Verification

**Files:**
- Modify: `src/bilianalysis/engine/__init__.py`

- [ ] **Step 1: Update __init__.py**

Replace `src/bilianalysis/engine/__init__.py`:

```python
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
            raise ImportError("PySpark is not installed. Install with: uv add pyspark")
        return SparkEngine(config.data)
    return PandasEngine(config.data)


__all__ = [
    "AnalysisEngine", "PandasEngine", "SparkEngine", "create_engine",
    "CleanReport",
    "OverallStats", "CategoryStats", "CreatorStats", "WeeklyTrend", "StatReport",
    "ClusterGroup", "ClusterResult", "ClusterReport",
    "PredictionResult", "PredictionReport",
]
```

- [ ] **Step 2: Verify factory import**

Run: `uv run python -c "from bilianalysis.engine import PandasEngine, SparkEngine, create_engine; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verify factory creates correct engine**

Run:
```bash
uv run python -c "
from bilianalysis.config import AppConfig, AnalysisSection
from bilianalysis.engine import create_engine, PandasEngine, SparkEngine

cfg_pandas = AppConfig(analysis=AnalysisSection(engine='pandas'))
cfg_spark = AppConfig(analysis=AnalysisSection(engine='spark'))

e1 = create_engine(cfg_pandas)
e2 = create_engine(cfg_spark)
print(f'pandas: {type(e1).__name__}')
print(f'spark: {type(e2).__name__}')
e2._spark.stop()
"
```
Expected:
```
pandas: PandasEngine
spark: SparkEngine
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (~79 total)

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/engine/__init__.py
git commit -m "feat: add create_engine() factory for dual-engine switching"
```
