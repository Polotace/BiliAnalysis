"""Spark 分析引擎实现。"""
import os
import sys
import tempfile
import time
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, monotonically_increasing_id, when, lit, explode
from pyspark.sql.types import LongType, DoubleType

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


def _ensure_hadoop_home() -> None:
    """Ensure HADOOP_HOME is set on Windows so Hadoop Shell can initialise.

    Creates a dummy hadoop home with winutils.exe (copied from cmd.exe).
    When Hadoop invokes winutils.exe, it exits 0 — permission-set calls
    during mkdirs become no-ops, but the write still succeeds.
    """
    if sys.platform != "win32":
        return
    if os.environ.get("HADOOP_HOME") or os.environ.get("hadoop.home.dir"):
        return
    hadoop_dir = Path(tempfile.gettempdir()) / ".bili-hadoop-home"
    bin_dir = hadoop_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    winutils = bin_dir / "winutils.exe"
    if not winutils.exists():
        import shutil
        shutil.copy2(os.environ.get("ComSpec", "C:\\Windows\\System32\\cmd.exe"), str(winutils))
    os.environ["HADOOP_HOME"] = str(hadoop_dir)


class SparkEngine(AnalysisEngine):
    """基于 PySpark 的分析引擎。

    全量加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """

    def __init__(self, data_config: DataSection):
        _ensure_hadoop_home()
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

        # 1. 全量加载 week_*.json（不读 progress.json）
        # Use Python glob on Windows — Spark's Hadoop glob requires native libs
        raw_files = sorted(self._raw_dir.glob("week_*.json"))
        raw_paths = [str(p) for p in raw_files]
        raw_df = self._spark.read.json(raw_paths)

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

        # Videos — explode 数组，每个视频一行
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

        # rcmd_reason may be absent from test fixtures
        v_fields = {f.name for f in video_rows.schema["v"].dataType.fields}
        if "rcmd_reason" in v_fields:
            category = video_rows.select(
                col("v.tid").alias("tid"),
                col("v.tname").alias("tname"),
                col("v.rcmd_reason.tid_v2").alias("tid_v2"),
                col("v.rcmd_reason.tname_v2").alias("tname_v2"),
                monotonically_increasing_id().alias("row_id"),
            )
        else:
            category = video_rows.select(
                col("v.tid").alias("tid"),
                col("v.tname").alias("tname"),
                lit(None).cast(LongType()).alias("tid_v2"),
                lit(None).cast("string").alias("tname_v2"),
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
            for c, t in df.dtypes:
                if t == "string":
                    df = df.na.fill("", subset=[c])
            dfs[name] = df
        return dfs

    def _convert_types(self, dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
        """统一各表列类型。"""
        # VideoStat: 数值 → double, aid → long
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
        raise NotImplementedError("prediction: to be implemented in Task 5")
