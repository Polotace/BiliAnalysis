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
from bilianalysis.nlp.keywords import KeywordsReport
from bilianalysis.engine.spark._helpers import HDFS_RAW, HDFS_PROCESSED
from bilianalysis.engine.spark.clean import clean_data_impl
from bilianalysis.engine.spark.analysis import (
    compute_statistics, compute_clustering, compute_prediction, compute_keywords,
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
                client.upload(f"{self.HDFS_RAW}", str(f), overwrite=True)
                uploaded += 1
        return uploaded

    # ── Raw file sync check ──────────────────────────────────

    def check_raw_sync(self) -> dict:
        """Compare local ``data/raw/`` with HDFS ``/user/hadoop/bilibili/raw/``.

        Returns ``{local_only, hdfs_only, in_sync}`` lists of filenames.
        WebHDFS unreachable → returns ``None`` for hdfs files.
        """
        local_files = sorted([f.name for f in self._raw_dir.glob("week_*.json")])
        hdfs_files = None
        try:
            from hdfs import InsecureClient
            client = InsecureClient(self._webhdfs_url, user="hadoop")
            hdfs_files = sorted([
                fname for fname in client.list(self.HDFS_RAW)
                if fname.startswith("week_") and fname.endswith(".json")
            ])
        except Exception:
            pass

        if hdfs_files is None:
            return {"local": local_files, "hdfs": None, "local_only": local_files, "in_sync": []}

        local_set = set(local_files)
        hdfs_set = set(hdfs_files)
        return {
            "local": local_files,
            "hdfs": hdfs_files,
            "local_only": sorted(local_set - hdfs_set),
            "hdfs_only": sorted(hdfs_set - local_set),
            "in_sync": sorted(local_set & hdfs_set),
        }

    # ── Pre-flight check ─────────────────────────────────────

    def _ensure_ready(self) -> None:
        """Verify raw + processed data are available; fix if possible.

        1. Check local ``data/raw/week_*.json`` exist
        2. Sync missing files to HDFS (upload)
        3. Check HDFS processed Parquet (schema + existence)
        4. Auto-trigger ``clean_data`` if needed
        """
        # 1. Raw files must exist locally
        raw_files = sorted(self._raw_dir.glob("week_*.json"))
        if not raw_files:
            raise RuntimeError(
                f"No week_*.json files found in {self._raw_dir}. "
                f"Run the crawler first."
            )
        print(f"[spark] Found {len(raw_files)} raw week file(s) locally")

        # 2. Sync raw to HDFS (upload missing). If upload fails, verify via Spark.
        synced = 0
        try:
            synced = self._sync_raw_to_hdfs()
            if synced > 0:
                print(f"[spark] Uploaded {synced} missing raw file(s) to HDFS {self.HDFS_RAW}/")
        except Exception as exc:
            import traceback
            print(f"[spark] WARNING: WebHDFS sync failed ({exc})")
            traceback.print_exc()
            # Verify raw files are actually accessible via Spark
            try:
                test_count = self._get_spark().read \
                    .option("multiline", "true") \
                    .json(f"{self.HDFS_RAW}/week_*.json") \
                    .count()
                if test_count == 0:
                    raise RuntimeError("Spark read returned 0 rows")
                print(f"[spark] HDFS raw data verified via Spark ({test_count} weeks)")
            except Exception as vexc:
                raise RuntimeError(
                    f"WebHDFS upload failed and no raw data found on HDFS. "
                    f"Fix WebHDFS connectivity ({self._webhdfs_url}) and retry. "
                    f"Upload error: {exc}"
                ) from vexc

        # 3. Check processed Parquet (schema + existence)
        weekly_path = f"{self.HDFS_PROCESSED}/Weekly"
        try:
            df = self._get_spark().read.parquet(weekly_path)
            video_path = f"{self.HDFS_PROCESSED}/Video"
            video = self._get_spark().read.parquet(video_path)
            if "week_number" not in video.columns:
                raise RuntimeError("Video parquet missing week_number — schema outdated")
            df.take(1)
            print(f"[spark] Processed data ready ({self.HDFS_PROCESSED}/)")
            return
        except Exception:
            pass

        # 4. Missing or outdated — run clean_data
        print(f"[spark] Processed data missing or outdated, running clean_data …")
        safe_run_async(self.clean_data())
        try:
            self._get_spark().read.parquet(weekly_path).take(1)
        except Exception as exc:
            raise RuntimeError(
                f"clean_data completed but {weekly_path} still unreadable"
            ) from exc

    # ── AnalysisEngine interface ─────────────────────────────

    async def clean_data(self) -> CleanReport:
        raw_files = sorted(self._raw_dir.glob("week_*.json"))
        raw_paths = [f"{self.HDFS_RAW}/week_*.json"] if raw_files else []
        total_weeks = len(raw_files)
        return clean_data_impl(self._get_spark(), raw_paths,
                               self.HDFS_PROCESSED, total_weeks)

    def statistics(self) -> StatReport:
        self._ensure_ready()
        return compute_statistics(self._get_spark(), self.HDFS_PROCESSED)

    def clustering(self) -> ClusterReport:
        self._ensure_ready()
        return compute_clustering(self._get_spark(), self.HDFS_PROCESSED)

    def prediction(self) -> PredictionReport:
        self._ensure_ready()
        return compute_prediction(self._get_spark(), self.HDFS_PROCESSED)

    def keywords(self) -> "KeywordsReport":
        self._ensure_ready()
        return compute_keywords(self._get_spark(), self.HDFS_PROCESSED)

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
