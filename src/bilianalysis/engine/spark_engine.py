"""Spark 分析引擎实现——支持本地和 HDFS 读写。"""
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, monotonically_increasing_id, when, lit, explode,
    avg, count, sum as spark_sum, collect_list,
)
from pyspark.sql.types import LongType, DoubleType

from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.clustering import KMeans as SparkKMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


def _ensure_hadoop_home() -> None:
    """Ensure HADOOP_HOME is set on Windows so Hadoop Shell can initialize.

    Creates a dummy hadoop home with winutils.exe (copied from cmd.exe).
    When Hadoop invokes winutils.exe, it exits 0 — permission-set calls
    during mkdirs become no-ops, but the writer still succeeds.
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

    可选 HDFS 集成：传入 hdfs_url 后自动启用 HDFS 读写路径。
    """

    def __init__(
        self,
        data_config: DataSection,
        hdfs_url: Optional[str] = None,
        hdfs_user: Optional[str] = None,
    ):
        _ensure_hadoop_home()
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)

        # Optional HDFS client for file management (list/upload/download)
        self._hdfs = None
        self._hdfs_enabled = False
        if hdfs_url:
            from hdfs import InsecureClient
            self._hdfs = InsecureClient(hdfs_url, user=hdfs_user or "hadoop")
            self._hdfs_enabled = True

        self._spark = (
            SparkSession.builder
            .appName("BiliAnalysis")
            .master("local[*]")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .getOrCreate()
        )

    # ── HDFS helpers ──────────────────────────────────────────

    def _hdfs_upload_dir(self, local_dir: Path, hdfs_dir: str) -> None:
        """Upload all Parquet files from local_dir to HDFS."""
        if not self._hdfs:
            return
        self._hdfs.makedirs(hdfs_dir)
        for f in local_dir.glob("*.parquet"):
            self._hdfs.upload(str(f), f"{hdfs_dir}/{f.name}", overwrite=True)

    def _hdfs_download_dir(self, hdfs_dir: str, local_dir: Path) -> None:
        """Download all JSON files from HDFS dir to local_dir."""
        if not self._hdfs:
            return
        local_dir.mkdir(parents=True, exist_ok=True)
        for fname in self._hdfs.list(hdfs_dir):
            if fname.startswith("week_") and fname.endswith(".json"):
                self._hdfs.download(f"{hdfs_dir}/{fname}", str(local_dir / fname), overwrite=True)

    # ── clean_data ───────────────────────────────────────────

    async def clean_data(self) -> CleanReport:
        """全量加载 raw JSON → 清洗 → 写出 5 张 Parquet。"""
        start_time = time.monotonic()

        # 0. 如果启用了 HDFS，先从 HDFS 拉取 raw JSON 到本地
        if self._hdfs_enabled:
            self._hdfs_download_dir("/data/raw", self._raw_dir)

        # 1. 全量加载 week_*.json（不读 progress.json）
        # Use Python glob on Windows — Spark's Hadoop glob requires native libs
        raw_files = sorted(self._raw_dir.glob("week_*.json"))
        raw_paths = [str(p) for p in raw_files]
        raw_df = self._spark.read.json(raw_paths)

        total_weeks = len(raw_files)

        # 2. 拆表 + row_id
        dfs = self._extract_tables(raw_df)

        # 3. 计数缺失值（填充前）
        missing_filled = self._count_nulls(dfs)

        # 4. 缺失值填充
        dfs = self._fill_missing(dfs)

        # 5. 去重（按 aid）
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

        # 6. 类型转换
        dfs = self._convert_types(dfs)

        # 7. 异常值检测
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

        # 8. 写出 Parquet（全量覆盖）
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        for f in self._processed_dir.glob("*.parquet"):
            f.unlink()
        for table_name, df in dfs.items():
            out_path = str(self._processed_dir / table_name)
            df.write.mode("overwrite").parquet(out_path)

        total_videos = dfs["Video"].count()

        # 9. 如果启用了 HDFS，上传 processed Parquet 到 HDFS
        if self._hdfs_enabled:
            self._hdfs_upload_dir(self._processed_dir, "/data/processed")

        duration = time.monotonic() - start_time
        return CleanReport(
            total_weeks=total_weeks, total_videos=total_videos,
            duplicates_dropped=duplicates_dropped, missing_filled=missing_filled,
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

    @staticmethod
    def _count_nulls(dfs: dict[str, DataFrame]) -> int:
        """Count total null values across all DataFrames (single agg per table)."""
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

    def _fill_missing(self, dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
        """缺失值填充：数值 → 0，字符串 → \"\"。"""
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

        # 3. 周匹配: pubdate between start_time and end_time
        df = df.crossJoin(weekly.withColumnRenamed("start_time", "w_start")
                           .withColumnRenamed("end_time", "w_end")
                           .withColumnRenamed("number", "week_number"))
        df = df.filter((col("pubdate") >= col("w_start")) & (col("pubdate") <= col("w_end")))

        # 4. 交互率
        df = df.withColumn("like_rate", col("like") / when(col("view") == 0, lit(1)).otherwise(col("view")))
        df = df.withColumn("coin_rate", col("coin") / when(col("view") == 0, lit(1)).otherwise(col("view")))
        df = df.withColumn("favorite_rate", col("favorite") / when(col("view") == 0, lit(1)).otherwise(col("view")))

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
            avg_interaction_rate=round(float(r["avg(like_rate)"]), 4),
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

    # ── clustering ───────────────────────────────────────────

    def clustering(self) -> ClusterReport:
        """从 processed/ Stat 读取 → KMeans(k=3) → ClusterReport。

        全 Spark 实现：聚类、聚合、标签分配均在 Spark 完成，
        仅将聚合后的小结果 collect 到 driver。"""
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

        # Silhouette score
        evaluator = ClusteringEvaluator(featuresCol="scaled_features", metricName="silhouette")
        sil_score = evaluator.evaluate(predictions)

        # Feature importance: variance of cluster centers
        centers = model.clusterCenters()
        import pandas as pd
        centers_df = pd.DataFrame([c.tolist() for c in centers], columns=features)
        importance = {f: round(float(centers_df[f].var()), 4) for f in features}

        # ── Pure Spark cluster analysis ──
        # Join predictions (aid + label) with stat (all features) on aid
        labeled = predictions.select("aid", "label").join(stat, "aid", "inner")

        # Per-cluster aggregations — one groupBy, collect 3 rows to driver
        cluster_agg = labeled.groupBy("label").agg(
            count("*").alias("cnt"),
            avg("view").alias("avg_view"),
            avg("like").alias("avg_like"),
            avg("coin").alias("avg_coin"),
            avg("favorite").alias("avg_favorite"),
        ).collect()  # only 3 rows → safe to collect

        # Rank by avg_view → assign Chinese tags
        label_view_rank = {row["label"]: float(row["avg_view"]) for row in cluster_agg}
        sorted_labels = sorted(label_view_rank, key=label_view_rank.get, reverse=True)
        tag_map = {sorted_labels[0]: "爆款视频", sorted_labels[1]: "普通热门", sorted_labels[2]: "潜力视频"}

        clusters = []
        for row in cluster_agg:
            label_idx = row["label"]
            # Sample aids (limit 20) — toPandas on 20 rows is cheap
            sample_pd = (
                labeled.filter(col("label") == label_idx)
                .select("aid").limit(20).toPandas()
            )
            sample_ids = sample_pd["aid"].astype(int).tolist()

            clusters.append(ClusterGroup(
                label=label_idx,
                tag=tag_map[label_idx],
                count=int(row["cnt"]),
                centroid={
                    "view": round(float(row["avg_view"]), 2),
                    "like": round(float(row["avg_like"]), 2),
                    "coin": round(float(row["avg_coin"]), 2),
                    "favorite": round(float(row["avg_favorite"]), 2),
                },
                avg_view=round(float(row["avg_view"]), 2),
                avg_like=round(float(row["avg_like"]), 2),
                avg_coin=round(float(row["avg_coin"]), 2),
                avg_favorite=round(float(row["avg_favorite"]), 2),
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

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet → 周聚合 → LinearRegression → PredictionReport。

        周聚合在 Spark 完成，转为小规模 Pandas DataFrame 后用 sklearn 拟合。
        每周仅一行，toPandas 安全。"""
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

        # 周聚合结果很小（每周一行），toPandas 安全
        df = weekly_agg.toPandas()

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
