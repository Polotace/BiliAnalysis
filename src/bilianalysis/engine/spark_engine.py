"""Spark 4.1.2 分析引擎 — Spark Connect + HDFS。"""
import threading
import time
from pathlib import Path

from pyspark.sql import SparkSession

from bilianalysis.utils.async_utils import safe_run_async
from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
)
from bilianalysis.engine.spark._helpers import HDFS_RAW, HDFS_PROCESSED
from bilianalysis.engine.spark.clean import clean_data_impl
from bilianalysis.engine.spark.analysis import (
    compute_statistics, compute_clustering, compute_prediction,
)


class SparkEngine(AnalysisEngine):
    """PySpark 4.1.2 分析引擎 — Spark Connect + HDFS。

    通过 gRPC 连接远程 Spark Connect 服务端。
    HDFS 数据路径由 Spark 服务端 ``fs.defaultFS`` 解析。
    原始文件通过 WebHDFS 上传。

    Parameters
    ----------
    data_config : DataSection
        数据路径配置。
    spark_remote : str
        Spark Connect gRPC 端点（如 ``"sc://hostname:15002"``）。
    webhdfs_url : str
        WebHDFS REST API URL（如 ``"http://namenode:9870"``）。
    """

    HDFS_RAW = HDFS_RAW
    HDFS_PROCESSED = HDFS_PROCESSED

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
            # ── Adaptive Query Execution ──
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.adaptive.advisoryPartitionSizeInBytes", "16MB")
            # ── Shuffle / parallelism (tiny dataset: ~300 weeks × 30 videos) ──
            .config("spark.sql.shuffle.partitions", "8")
            # ── Join optimization ──
            .config("spark.sql.autoBroadcastJoinThreshold", "50MB")
            # ── Arrow (faster toPandas / collect) ──
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            # ── gRPC (larger messages for toPandas results) ──
            .config("spark.connect.grpc.maxMessageSize", "128MB")
            .getOrCreate()
        )

    # ── HDFS sync ────────────────────────────────────────────

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
        """Probe HDFS for ``Weekly`` parquet with correct schema; auto-trigger clean_data if missing or stale."""
        weekly_path = f"{self.HDFS_PROCESSED}/Weekly"
        try:
            df = self._get_spark().read.parquet(weekly_path)
            # Schema check: new code requires `week_number` column on Video table
            video_path = f"{self.HDFS_PROCESSED}/Video"
            video = self._get_spark().read.parquet(video_path)
            if "week_number" not in video.columns:
                raise RuntimeError("Video parquet missing week_number — schema outdated")
            df.take(1)
            return
        except Exception:
            pass
        safe_run_async(self.clean_data())
        try:
            self._get_spark().read.parquet(weekly_path).take(1)
        except Exception as exc:
            raise RuntimeError(
                f"clean_data completed but {weekly_path} still unreadable"
            ) from exc

    # ── AnalysisEngine interface ─────────────────────────────

    async def clean_data(self) -> CleanReport:
        synced = self._sync_raw_to_hdfs()
        if synced > 0:
            print(f"[spark] Synced {synced} raw file(s) to HDFS {self.HDFS_RAW}/")
        raw_files = sorted(self._raw_dir.glob("week_*.json"))
        raw_paths = [str(p) for p in raw_files]
        return clean_data_impl(self._get_spark(), raw_paths,
                               self.HDFS_PROCESSED, len(raw_files))

    def statistics(self) -> StatReport:
        self._ensure_processed()
        return compute_statistics(self._get_spark(), self.HDFS_PROCESSED)

    def clustering(self) -> ClusterReport:
        self._ensure_processed()
        return compute_clustering(self._get_spark(), self.HDFS_PROCESSED)

    def prediction(self) -> PredictionReport:
        self._ensure_processed()
        return compute_prediction(self._get_spark(), self.HDFS_PROCESSED)

    def model_comparison(self) -> "ModelComparisonReport":
        raise NotImplementedError(
            "model_comparison 依赖 sklearn 多模型交叉验证，SparkEngine 不支持。"
            "请使用 PandasEngine (analysis.engine: pandas)。"
        )

    # ── health check ─────────────────────────────────────────

    def ping(self, timeout_seconds: float = 10.0) -> bool:
        """Check Spark connectivity with ``SELECT 1``. Returns True or raises."""
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
        """Check WebHDFS connectivity."""
        from hdfs import InsecureClient
        client = InsecureClient(self._webhdfs_url, user="hadoop")
        client.status("/")
        return {"backend": "webhdfs", "ok": True}
