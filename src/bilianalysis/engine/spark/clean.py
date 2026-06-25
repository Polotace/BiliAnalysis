"""Data cleaning: raw JSON → 5 Parquet tables."""
import time
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, monotonically_increasing_id, when, lit, explode,
    count, sum as spark_sum,
)
from pyspark.sql.types import LongType, DoubleType

from bilianalysis.engine.base import CleanReport


def extract_tables(raw_df: DataFrame) -> dict[str, DataFrame]:
    """从 raw Spark DataFrame 拆出 5 张表，每行带统一 row_id。"""
    weekly = raw_df.select(
        col("number"),
        col("config.subject").cast("string").alias("subject"),
        col("config.name").cast("string").alias("name"),
        col("config.stime").cast("long").alias("start_time"),
        col("config.etime").cast("long").alias("end_time"),
    )

    video_rows = raw_df.select(
        col("number").alias("week_number"),
        explode("videos").alias("v")
    ).withColumn("row_id", monotonically_increasing_id())

    video = video_rows.select(
        "row_id", "week_number",
        col("v.aid").alias("aid"), col("v.bvid").alias("bvid"),
        col("v.title").alias("title"), col("v.desc").alias("desc"),
        col("v.duration").alias("duration"), col("v.pubdate").alias("pubdate"),
        col("v.cid").alias("cid"), col("v.pic").alias("pic"),
    )

    creator = video_rows.select(
        "row_id",
        col("v.owner.mid").alias("mid"),
        col("v.owner.name").alias("name"),
        col("v.owner.face").alias("face"),
    )

    category = video_rows.select(
        "row_id",
        col("v.tid").alias("tid"), col("v.tname").alias("tname"),
        lit(None).cast(LongType()).alias("tid_v2"),
        lit(None).cast("string").alias("tname_v2"),
    )

    stat = video_rows.select(
        "row_id",
        col("v.stat.aid").alias("aid"),
        col("v.stat.view").alias("view"), col("v.stat.like").alias("like"),
        col("v.stat.coin").alias("coin"), col("v.stat.favorite").alias("favorite"),
        col("v.stat.share").alias("share"), col("v.stat.reply").alias("reply"),
        col("v.stat.danmaku").alias("danmaku"),
    )

    return {
        "Weekly": weekly, "Video": video, "Creator": creator,
        "Category": category, "VideoStat": stat,
    }


def count_nulls(dfs: dict[str, DataFrame]) -> int:
    """Count total null values across all DataFrames."""
    total = 0
    for df in dfs.values():
        null_exprs = [
            spark_sum(when(col(c).isNull(), 1).otherwise(0)).alias(c)
            for c in df.columns
        ]
        if null_exprs:
            row = df.agg(*null_exprs).collect()[0]
            total += sum(int(row[c]) for c in df.columns)
    return total


def fill_missing(dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
    """缺失值填充：数值 → 0，字符串 → \"\"."""
    numeric_defaults = {
        "Weekly": {"start_time": 0, "end_time": 0},
        "Video": {"aid": 0, "duration": 0, "cid": 0, "pubdate": 0},
        "Creator": {"mid": 0},
        "Category": {"tid": 0, "tid_v2": 0},
        "VideoStat": {"aid": 0, "view": 0, "like": 0, "coin": 0,
                      "favorite": 0, "share": 0, "reply": 0, "danmaku": 0},
    }
    for name, df in dfs.items():
        defaults = numeric_defaults.get(name, {})
        fill_map = {k: v for k, v in defaults.items() if k in df.columns}
        if fill_map:
            df = df.na.fill(fill_map)
        for c, t in df.dtypes:
            if t == "string":
                df = df.na.fill("", subset=[c])
        dfs[name] = df
    return dfs


def convert_types(dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
    """统一各表列类型。"""
    for cn in ["view", "like", "coin", "favorite", "share", "reply", "danmaku"]:
        if cn in dfs["VideoStat"].columns:
            dfs["VideoStat"] = dfs["VideoStat"].withColumn(cn, col(cn).cast(DoubleType()))
    for cn in ["aid"]:
        if cn in dfs["VideoStat"].columns:
            dfs["VideoStat"] = dfs["VideoStat"].withColumn(cn, col(cn).cast(LongType()))
    for cn in ["aid", "duration", "cid", "pubdate"]:
        if cn in dfs["Video"].columns:
            dfs["Video"] = dfs["Video"].withColumn(cn, col(cn).cast(LongType()))
    if "mid" in dfs["Creator"].columns:
        dfs["Creator"] = dfs["Creator"].withColumn("mid", col("mid").cast(LongType()))
    for cn in ["tid", "tid_v2"]:
        if cn in dfs["Category"].columns:
            dfs["Category"] = dfs["Category"].withColumn(cn, col(cn).cast(LongType()))
    if "number" in dfs["Weekly"].columns:
        dfs["Weekly"] = dfs["Weekly"].withColumn("number", col("number").cast(LongType()))
    return dfs


def clean_data_impl(spark: SparkSession, raw_paths: list[str],
                    processed_path: str, total_weeks: int) -> CleanReport:
    """Full clean pipeline: raw JSON → Parquet.  Pure function."""
    start_time = time.monotonic()
    raw_df = spark.read.option("multiline", "true").json(raw_paths)

    dfs = extract_tables(raw_df)
    missing_filled = count_nulls(dfs)
    dfs = fill_missing(dfs)

    video_df = dfs["Video"]
    before = video_df.count()
    video_df = video_df.dropDuplicates(["aid"])
    duplicates_dropped = before - video_df.count()
    dfs["Video"] = video_df
    kept_ids = video_df.select("row_id")
    dfs["VideoStat"] = dfs["VideoStat"].join(kept_ids, "row_id", "inner")
    dfs["Creator"] = dfs["Creator"].join(kept_ids, "row_id", "inner")
    dfs["Category"] = dfs["Category"].join(kept_ids, "row_id", "inner")

    dfs = convert_types(dfs)

    stat_df = dfs["VideoStat"]
    stat_before = stat_df.count()
    valid = (
        (col("view") >= 0) & (col("like") >= 0) & (col("coin") >= 0) &
        (col("favorite") >= 0) & (col("share") >= 0) & (col("reply") >= 0) &
        (col("danmaku") >= 0)
    )
    dfs["VideoStat"] = stat_df.filter(valid)
    outliers_flagged = stat_before - dfs["VideoStat"].count()
    valid_ids = dfs["VideoStat"].select("row_id")
    dfs["Video"] = dfs["Video"].join(valid_ids, "row_id", "inner")
    dfs["Creator"] = dfs["Creator"].join(valid_ids, "row_id", "inner")
    dfs["Category"] = dfs["Category"].join(valid_ids, "row_id", "inner")

    for table_name, df in dfs.items():
        df.write.mode("overwrite").parquet(f"{processed_path}/{table_name}")

    total_videos = dfs["Video"].count()
    duration = time.monotonic() - start_time
    return CleanReport(
        total_weeks=total_weeks, total_videos=total_videos,
        duplicates_dropped=duplicates_dropped, missing_filled=missing_filled,
        outliers_flagged=outliers_flagged, duration_seconds=round(duration, 2),
    )
