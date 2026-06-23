"""Spark 3.5.8 分析引擎 — Spark Connect + HDFS。"""
import threading
import time
from pathlib import Path

from bilianalysis.utils.async_utils import safe_run_async

import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, monotonically_increasing_id, when, lit, explode,
    avg, count, sum as spark_sum, collect_list,
)
from pyspark.sql.types import LongType, DoubleType

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, silhouette_score
from sklearn.preprocessing import StandardScaler as SklearnStandardScaler
from sklearn.cluster import KMeans as SklearnKMeans
from sklearn.decomposition import PCA

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


class SparkEngine(AnalysisEngine):
    """PySpark 3.5.8 分析引擎 — Spark Connect + HDFS 专用。

    通过 gRPC 连接远程 Spark Connect 服务端，所有数据存储在 HDFS：
    ``/user/hadoop/bilibili/raw/``（原始 JSON）
    ``/user/hadoop/bilibili/processed/``（清洗后 Parquet）。

    clustering 使用 sklearn 实现（KMeans + PCA），
    因为 ``pyspark.ml`` 在 Spark 3.5 Connect 中不受支持。
    model_comparison 请使用 PandasEngine。

    Parameters
    ----------
    data_config : DataSection
        数据路径配置。
    spark_remote : str
        Spark Connect gRPC 端点。
    webhdfs_url : str
        WebHDFS REST API URL（如 ``"http://namenode:9870"``）。
    """

    HDFS_RAW = "/user/hadoop/bilibili/raw"
    HDFS_PROCESSED = "/user/hadoop/bilibili/processed"

    def __init__(
        self,
        data_config: DataSection,
        spark_remote: str,
        webhdfs_url: str,
    ):
        import os
        if not spark_remote:
            spark_remote = os.environ.get("SPARK_REMOTE", "")
        if not spark_remote:
            raise ValueError(
                "spark_remote is required. Set it in config or via SPARK_REMOTE env var."
            )
        self._spark_remote = spark_remote
        self._webhdfs_url = webhdfs_url

        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)

        # SparkSession — lazy, created on first _get_spark() call
        self._spark: SparkSession | None = None
        self._spark_verified_at: float = 0.0

    # ── SparkSession (lazy + auto-reconnect) ─────────────────

    def _get_spark(self) -> SparkSession:
        """Return the SparkSession, creating or reconnecting as needed."""
        now = time.monotonic()

        if self._spark is None:
            self._spark = self._create_session()
            self._spark_verified_at = now
            return self._spark

        # Re-verify session liveness every 60 s (handles server restart)
        if now - self._spark_verified_at > 60:
            try:
                self._spark.sql("SELECT 1").collect()
                self._spark_verified_at = now
            except Exception:
                try:
                    self._spark.stop()
                except Exception:
                    pass
                self._spark = self._create_session()
                self._spark_verified_at = time.monotonic()

        return self._spark

    def _create_session(self) -> SparkSession:
        return (
            SparkSession.builder
            .appName("BiliAnalysis")
            .remote(self._spark_remote)
            .getOrCreate()
        )

    # ── Raw file sync ────────────────────────────────────────

    def _sync_raw_to_hdfs(self) -> int:
        """Upload local ``week_*.json`` files missing on HDFS, via WebHDFS."""
        from hdfs import InsecureClient

        client = InsecureClient(self._webhdfs_url, user="hadoop")
        try:
            client.makedirs(self.HDFS_RAW)
        except Exception:
            pass

        try:
            hdfs_files = {
                fname for fname in client.list(self.HDFS_RAW)
                if fname.startswith("week_") and fname.endswith(".json")
            }
        except Exception:
            hdfs_files = set()

        local_files = sorted(self._raw_dir.glob("week_*.json"))
        uploaded = 0
        for f in local_files:
            if f.name not in hdfs_files:
                client.upload(str(f), f"{self.HDFS_RAW}/{f.name}", overwrite=True)
                uploaded += 1
        return uploaded

    # ── Lazy clean_data ──────────────────────────────────────

    def _ensure_processed(self) -> None:
        """Probe HDFS for ``Weekly`` parquet; auto-trigger clean_data if missing."""
        hdfs_path = f"{self.HDFS_PROCESSED}/Weekly"
        try:
            self._get_spark().read.parquet(hdfs_path).take(1)
            return
        except Exception:
            pass

        safe_run_async(self.clean_data())

        try:
            self._get_spark().read.parquet(hdfs_path).take(1)
        except Exception as exc:
            raise RuntimeError(
                f"clean_data completed but {hdfs_path} still unreadable"
            ) from exc

    # ── clean_data ───────────────────────────────────────────

    async def clean_data(self) -> CleanReport:
        """加载 raw JSON (HDFS) → 清洗 → 写出 5 张 Parquet (HDFS)。"""
        start_time = time.monotonic()

        synced = self._sync_raw_to_hdfs()
        if synced > 0:
            print(f"[spark] Synced {synced} raw file(s) to HDFS {self.HDFS_RAW}/")

        raw_path = f"{self.HDFS_RAW}/week_*.json"
        print(f"[spark] Reading raw JSON from {raw_path}")
        raw_df = self._get_spark().read.option("multiline", "true").json(raw_path)

        schema_cols = raw_df.columns
        print(f"[spark] Raw schema: {schema_cols}")
        if "number" not in schema_cols:
            raise RuntimeError(
                f"Failed to parse JSON from {raw_path}. "
                f"Schema={schema_cols} — all rows may be corrupt. "
                f"Try: hdfs dfs -cat {self.HDFS_RAW}/week_001.json | head -c 200"
            )

        total_weeks = raw_df.select("number").distinct().count()

        dfs = self._extract_tables(raw_df)
        missing_filled = self._count_nulls(dfs)
        dfs = self._fill_missing(dfs)

        # Dedup
        video_df = dfs["Video"]
        before = video_df.count()
        video_df = video_df.dropDuplicates(["aid"])
        duplicates_dropped = before - video_df.count()
        dfs["Video"] = video_df
        kept_ids = video_df.select("row_id")
        dfs["VideoStat"] = dfs["VideoStat"].join(kept_ids, "row_id", "inner")
        dfs["Creator"] = dfs["Creator"].join(kept_ids, "row_id", "inner")
        dfs["Category"] = dfs["Category"].join(kept_ids, "row_id", "inner")

        dfs = self._convert_types(dfs)

        # Outlier filter
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

        # Write Parquet to HDFS
        proc = self.HDFS_PROCESSED
        for table_name, df in dfs.items():
            df.write.mode("overwrite").parquet(f"{proc}/{table_name}")

        total_videos = dfs["Video"].count()
        duration = time.monotonic() - start_time
        return CleanReport(
            total_weeks=total_weeks, total_videos=total_videos,
            duplicates_dropped=duplicates_dropped, missing_filled=missing_filled,
            outliers_flagged=outliers_flagged, duration_seconds=round(duration, 2),
        )

    # ── 清洗子步骤 ──────────────────────────────────────────

    def _extract_tables(self, raw_df: DataFrame) -> dict[str, DataFrame]:
        """从 raw Spark DataFrame 拆出 5 张表，每行带统一 row_id 用于关联。"""
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
            "row_id",
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

        # rcmd_reason is always a plain string in this dataset — null-fill
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

    @staticmethod
    def _count_nulls(dfs: dict[str, DataFrame]) -> int:
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
            for c, t in df.dtypes:
                if t == "string":
                    df = df.na.fill("", subset=[c])
            dfs[name] = df
        return dfs

    def _convert_types(self, dfs: dict[str, DataFrame]) -> dict[str, DataFrame]:
        for col_name in ["view", "like", "coin", "favorite", "share", "reply", "danmaku"]:
            if col_name in dfs["VideoStat"].columns:
                dfs["VideoStat"] = dfs["VideoStat"].withColumn(col_name, col(col_name).cast(DoubleType()))
        for col_name in ["aid"]:
            if col_name in dfs["VideoStat"].columns:
                dfs["VideoStat"] = dfs["VideoStat"].withColumn(col_name, col(col_name).cast(LongType()))
        for col_name in ["aid", "duration", "cid", "pubdate"]:
            if col_name in dfs["Video"].columns:
                dfs["Video"] = dfs["Video"].withColumn(col_name, col(col_name).cast(LongType()))
        if "mid" in dfs["Creator"].columns:
            dfs["Creator"] = dfs["Creator"].withColumn("mid", col("mid").cast(LongType()))
        for col_name in ["tid", "tid_v2"]:
            if col_name in dfs["Category"].columns:
                dfs["Category"] = dfs["Category"].withColumn(col_name, col(col_name).cast(LongType()))
        if "number" in dfs["Weekly"].columns:
            dfs["Weekly"] = dfs["Weekly"].withColumn("number", col("number").cast(LongType()))
        return dfs

    # ── statistics ───────────────────────────────────────────

    def statistics(self) -> StatReport:
        """HDFS Parquet → JOIN → groupBy 聚合 → StatReport。"""
        self._ensure_processed()
        proc = self.HDFS_PROCESSED
        weekly = self._get_spark().read.parquet(f"{proc}/Weekly")
        video = self._get_spark().read.parquet(f"{proc}/Video")
        stat = self._get_spark().read.parquet(f"{proc}/VideoStat")
        creator = self._get_spark().read.parquet(f"{proc}/Creator")
        category = self._get_spark().read.parquet(f"{proc}/Category")

        df = video.join(stat, "aid", "inner")
        df = df.join(creator, "row_id", "left")
        df = df.join(category, "row_id", "left")

        df = df.crossJoin(weekly.withColumnRenamed("start_time", "w_start")
                           .withColumnRenamed("end_time", "w_end")
                           .withColumnRenamed("number", "week_number"))
        df = df.filter((col("pubdate") >= col("w_start")) & (col("pubdate") <= col("w_end")))

        df = df.withColumn("like_rate", col("like") / when(col("view") == 0, lit(1)).otherwise(col("view")))
        df = df.withColumn("coin_rate", col("coin") / when(col("view") == 0, lit(1)).otherwise(col("view")))
        df = df.withColumn("favorite_rate", col("favorite") / when(col("view") == 0, lit(1)).otherwise(col("view")))

        overall_row = df.agg(
            count("aid").alias("total_videos"), count("mid").alias("total_creators"),
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

    # ── clustering (sklearn on Spark Connect) ────────────────

    def clustering(self) -> ClusterReport:
        """HDFS Parquet → toPandas → sklearn KMeans+PCA → ClusterReport。"""
        self._ensure_processed()
        start_time = time.monotonic()

        stat_spark = self._get_spark().read.parquet(f"{self.HDFS_PROCESSED}/VideoStat")
        total = stat_spark.count()
        if total < 3:
            duration = time.monotonic() - start_time
            return ClusterReport(
                clusters=ClusterResult(k=3, clusters=[], silhouette_score=0.0, feature_importance={}),
                scatter_data={"labels": [], "x": [], "y": []},
                duration_seconds=round(duration, 2),
            )

        features = ["view", "like", "coin", "favorite"]
        stat_pd = stat_spark.select(["aid"] + features).toPandas()
        X = stat_pd[features].values.astype(np.float64)

        scaler = SklearnStandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = SklearnKMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        sil_score = silhouette_score(X_scaled, labels)

        import pandas as pd
        centers = pd.DataFrame(kmeans.cluster_centers_, columns=features)
        importance = {f: round(float(centers[f].var()), 4) for f in features}

        stat_pd["label"] = labels
        label_view_rank = {
            label_idx: float(stat_pd.loc[stat_pd["label"] == label_idx, "view"].mean())
            for label_idx in range(3)
        }
        sorted_labels = sorted(label_view_rank, key=label_view_rank.get, reverse=True)
        tag_map = {sorted_labels[0]: "爆款视频", sorted_labels[1]: "普通热门", sorted_labels[2]: "潜力视频"}

        clusters = []
        for label_idx in range(3):
            mask = stat_pd["label"] == label_idx
            cluster_data = stat_pd[mask]
            cluster_X = X_scaled[mask.values]
            centroid = {f: round(float(cluster_X[:, i].mean()), 2) for i, f in enumerate(features)}
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

        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        scatter_data = {
            "labels": labels.tolist(),
            "x": [round(float(v), 4) for v in X_pca[:, 0].tolist()],
            "y": [round(float(v), 4) for v in X_pca[:, 1].tolist()],
        }

        duration = time.monotonic() - start_time
        return ClusterReport(
            clusters=ClusterResult(k=3, clusters=clusters,
                                   silhouette_score=round(float(sil_score), 4),
                                   feature_importance=importance),
            scatter_data=scatter_data,
            duration_seconds=round(duration, 2),
        )

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        """HDFS Parquet → 周聚合 → LinearRegression → PredictionReport。"""
        self._ensure_processed()
        start_time = time.monotonic()
        proc = self.HDFS_PROCESSED
        video = self._get_spark().read.parquet(f"{proc}/Video")
        stat = self._get_spark().read.parquet(f"{proc}/VideoStat")
        weekly = self._get_spark().read.parquet(f"{proc}/Weekly")

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
                 "actual": round(float(y[i]), 2), "predicted": round(float(y_pred[i]), 2)}
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

    # ── model_comparison ───────────────────────────────────────

    def model_comparison(self) -> "ModelComparisonReport":
        raise NotImplementedError(
            "model_comparison 依赖 sklearn 多模型交叉验证，SparkEngine 不支持。"
            "请使用 PandasEngine (analysis.engine: pandas)。"
        )

    # ── health check ─────────────────────────────────────────

    def ping(self, timeout_seconds: float = 10.0) -> bool:
        """Check Spark connectivity with ``SELECT 1``.  Returns True or raises."""
        import concurrent.futures

        def _try():
            self._get_spark().sql("SELECT 1").collect()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_try)
            try:
                future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise ConnectionError(
                    f"Spark ping timed out after {timeout_seconds}s "
                    f"({self._spark_remote}). Is the Connect server running?"
                ) from None
            except Exception as exc:
                raise ConnectionError(
                    f"Spark ping failed ({self._spark_remote}): {exc}"
                ) from exc
        return True

    def ping_hdfs(self) -> dict:
        """Check WebHDFS connectivity. Returns ``{"backend": "webhdfs", "ok": True}``."""
        from hdfs import InsecureClient
        client = InsecureClient(self._webhdfs_url, user="hadoop")
        client.status("/")
        return {"backend": "webhdfs", "ok": True}
