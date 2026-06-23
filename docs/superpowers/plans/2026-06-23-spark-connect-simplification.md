# Spark Connect 简化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 精简 SparkEngine：去掉 pyarrow 后端、hdfs_host/hdfs_port 配置、死代码，仅保留 WebHDFS 上传 + Spark 直读 HDFS 路径。

**Architecture:** 配置文件从 6 个 Spark 字段减为 5 个（`webhdfs_url` 替代 `hdfs_host`/`hdfs_port`）。SparkEngine 构造参数从 4 减为 3。Spark 数据路径不再拼接 `hdfs://` URI，直接用 `/user/hadoop/bilibili/raw`。`_safe_run_async` 提取为公共工具。

**Tech Stack:** Python 3.11, PySpark 3.5.8 (Connect), hdfs 库 (WebHDFS), Pydantic

---

### Task 1: 提取 `_safe_run_async` 为公共工具

**Files:**
- Create: `src/bilianalysis/utils/async_utils.py`
- Modify: `src/bilianalysis/engine/spark_engine.py:29-50`
- Modify: `src/bilianalysis/engine/pandas_engine.py:29-50`

- [ ] **Step 1: 创建公共工具模块**

```python
"""Async utilities shared across the codebase."""
import asyncio
import threading


def safe_run_async(coro):
    """Run an async coroutine from sync code — safe inside or outside event loops.

    Uses ``asyncio.run()`` when no loop is running; spawns a background
    thread when called from within an active event loop (e.g. inside a
    pipeline task).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_holder = []
    exc_holder = []

    def _target():
        try:
            result_holder.append(asyncio.run(coro))
        except Exception as exc:
            exc_holder.append(exc)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    if exc_holder:
        raise exc_holder[0]
    return result_holder[0] if result_holder else None
```

- [ ] **Step 2: 修改 `spark_engine.py` — 移除私有副本，改为 import**

删除第 12-39 行的 `_safe_run_async` 函数定义。在文件顶部的 import 区添加：

```python
from bilianalysis.utils.async_utils import safe_run_async
```

将 `_safe_run_async(self.clean_data())` 改为 `safe_run_async(self.clean_data())`。

- [ ] **Step 3: 修改 `pandas_engine.py` — 同上**

删除私有 `_safe_run_async`，改为 `from bilianalysis.utils.async_utils import safe_run_async`。更新调用点。

- [ ] **Step 4: 验证导入**

```bash
uv run python -c "from bilianalysis.utils.async_utils import safe_run_async; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/utils/async_utils.py src/bilianalysis/engine/spark_engine.py src/bilianalysis/engine/pandas_engine.py
git commit -m "refactor: extract safe_run_async to shared utility"
```

---

### Task 2: 更新 AnalysisSection 配置模型

**Files:**
- Modify: `src/bilianalysis/config/model.py:16-24`

- [ ] **Step 1: 替换 `hdfs_host` + `hdfs_port` 为 `webhdfs_url`**

```python
class AnalysisSection(BaseModel):
    """分析引擎配置节"""
    engine: Literal["pandas", "spark"] = "pandas"
    spark_remote: str | None = None            # Spark Connect gRPC 端点 "sc://host:15002"
    webhdfs_url: str | None = None             # WebHDFS REST API "http://host:9870"
    spark_ping_timeout: float = 10.0           # 启动后 Spark 连通检查超时秒数（0=跳过）
    spark_ping_retries: int = 3               # 连通检查最大重试次数
    spark_ping_retry_delay: float = 60.0      # 重试间隔秒数（默认 60s）
```

- [ ] **Step 2: 验证配置加载**

```bash
uv run python -c "
from bilianalysis.config.model import AnalysisSection
a = AnalysisSection()
assert a.webhdfs_url is None
a2 = AnalysisSection(webhdfs_url='http://nn:9870')
assert a2.webhdfs_url == 'http://nn:9870'
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/config/model.py
git commit -m "feat(config): replace hdfs_host/hdfs_port with webhdfs_url"
```

---

### Task 3: 重写 SparkEngine 构造函数和路径

**Files:**
- Modify: `src/bilianalysis/engine/spark_engine.py`

- [ ] **Step 1: 精简文件头部**

移除不再需要的 import：`pyarrow`（不再引用）、`concurrent.futures`（保留给 ping 用）、`urlparse`。

当前文件（~710 行），目标 ~500 行。

- [ ] **Step 2: 重写类常量、docstring、构造函数**

```python
class SparkEngine(AnalysisEngine):
    """PySpark 3.5.8 分析引擎 — Spark Connect + HDFS。

    通过 gRPC 连接远程 Spark Connect 服务端。
    数据路径由 Spark 服务端的 ``fs.defaultFS`` 解析。
    原始文件通过 WebHDFS 上传。

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

        self._spark: SparkSession | None = None
        self._spark_verified_at: float = 0.0
```

- [ ] **Step 3: 删除 `_hdfs_raw()` 和 `_hdfs_processed()` 方法，更新所有引用**

将所有 `self._hdfs_raw()` → `self.HDFS_RAW`，所有 `self._hdfs_processed()` → `self.HDFS_PROCESSED`。

- [ ] **Step 4: 重写 `_sync_raw_to_hdfs` — 仅 WebHDFS**

```python
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
```

- [ ] **Step 5: 重写 `ping_hdfs` — 仅 WebHDFS**

```python
def ping_hdfs(self) -> dict:
    """Check WebHDFS connectivity. Returns ``{"backend": "webhdfs", "ok": True}``."""
    from hdfs import InsecureClient
    client = InsecureClient(self._webhdfs_url, user="hadoop")
    client.status("/")
    return {"backend": "webhdfs", "ok": True}
```

- [ ] **Step 6: Commit**

```bash
git add src/bilianalysis/engine/spark_engine.py
git commit -m "refactor(spark): simplify to webhdfs-only, remove pyarrow backend and hdfs:// URI construction"
```

---

### Task 4: 清理 `_extract_tables` 死代码

**Files:**
- Modify: `src/bilianalysis/engine/spark_engine.py:_extract_tables`

- [ ] **Step 1: 简化 `rcmd_reason` 处理**

将第 338-356 行替换为始终 null-fill 的版本：

```python
# rcmd_reason may be absent or a plain string — always null-fill tid_v2/tname_v2
category = video_rows.select(
    "row_id",
    col("v.tid").alias("tid"), col("v.tname").alias("tname"),
    lit(None).cast(LongType()).alias("tid_v2"),
    lit(None).cast("string").alias("tname_v2"),
)
```

移除 `v_fields` 字典构造、`StructType` import、条件分支。

- [ ] **Step 2: Commit**

```bash
git add src/bilianalysis/engine/spark_engine.py
git commit -m "refactor(spark): remove dead rcmd_reason StructType branch"
```

---

### Task 5: 更新工厂函数

**Files:**
- Modify: `src/bilianalysis/engine/__init__.py`

- [ ] **Step 1: 更新 `create_engine` — 检查 `webhdfs_url` 并传递**

```python
def create_engine(config: AppConfig) -> AnalysisEngine:
    if config.analysis.engine == "spark":
        if not _HAS_SPARK:
            raise ImportError("PySpark is not installed. Install it firstly.")
        if not config.analysis.spark_remote:
            raise ValueError("spark_remote is required when engine=spark.")
        if not config.analysis.webhdfs_url:
            raise ValueError("webhdfs_url is required when engine=spark.")
        return SparkEngine(
            config.data,
            spark_remote=config.analysis.spark_remote,
            webhdfs_url=config.analysis.webhdfs_url,
        )
    return PandasEngine(config.data)
```

- [ ] **Step 2: Commit**

```bash
git add src/bilianalysis/engine/__init__.py
git commit -m "feat(engine): pass webhdfs_url to SparkEngine via factory"
```

---

### Task 6: 更新启动健康检查

**Files:**
- Modify: `app/api/app.py`

- [ ] **Step 1: 健康检查复用 API 引擎单例**

```python
async def _spark_health_check(app: FastAPI):
    cfg = config.analysis
    if cfg.spark_ping_timeout <= 0:
        print("[spark] Health check disabled (spark_ping_timeout=0)")
        return

    await asyncio.sleep(2)

    print(f"[spark] Checking connectivity to {cfg.spark_remote} "
          f"(timeout={cfg.spark_ping_timeout}s, retries={cfg.spark_ping_retries}) …")

    # Use the same engine singleton as the API
    from api.deps import _analysis_engine
    engine = _analysis_engine
    if engine is None:
        from bilianalysis.engine import create_engine
        engine = create_engine(config)

    for attempt in range(1, cfg.spark_ping_retries + 1):
        try:
            engine.ping(timeout_seconds=cfg.spark_ping_timeout)
            logger.info("Spark Connect ping OK (%s)", cfg.spark_remote)
            print(f"[spark] Connected to {cfg.spark_remote}")
            break
        except ConnectionError as exc:
            if attempt < cfg.spark_ping_retries:
                delay = cfg.spark_ping_retry_delay
                print(f"[spark] Attempt {attempt}/{cfg.spark_ping_retries} failed: {exc}")
                print(f"[spark] Retrying in {delay:.0f}s …")
                await asyncio.sleep(delay)
            else:
                print(f"[spark] FATAL: {cfg.spark_ping_retries} attempts failed. Shutting down.")
                sys.exit(1)
        except Exception as exc:
            logger.exception("Spark health check aborted: %s", exc)
            print(f"[spark] FATAL: unexpected error: {exc}")
            sys.exit(1)

    # Spark OK — check HDFS
    try:
        result = engine.ping_hdfs()
        print(f"[spark] HDFS reachable via {result['backend']} ({cfg.webhdfs_url})")
    except ConnectionError as exc:
        print(f"[spark] WARNING: HDFS unreachable: {exc}")
```

- [ ] **Step 2: 更新 lifespan 中的任务创建条件**

健康检查在 `engine=spark` 且 `spark_remote` 有值时总是启动（不再判断 `spark_ping_timeout`，判断已移到函数内部）。

- [ ] **Step 3: Commit**

```bash
git add app/api/app.py
git commit -m "fix(api): health check reuses engine singleton, avoids orphan session"
```

---

### Task 7: 更新配置文件

**Files:**
- Modify: `config.yaml`
- Modify: `config.example.yaml`

- [ ] **Step 1: 更新 `config.yaml`**

```yaml
analysis:
  engine: spark
  spark_remote: "sc://192.168.212.134:15002"
  webhdfs_url: "http://192.168.212.134:9870"
  # spark_ping_timeout: 10.0
  # spark_ping_retries: 3
  # spark_ping_retry_delay: 60.0
```

- [ ] **Step 2: 更新 `config.example.yaml`**

```yaml
analysis:
  engine: pandas
  # spark_remote: "sc://host:15002"
  # webhdfs_url: "http://host:9870"
```

- [ ] **Step 3: Commit**

```bash
git add config.yaml config.example.yaml
git commit -m "chore(config): update spark config for webhdfs_url"
```

---

### Task 8: 全量测试验证

- [ ] **Step 1: 运行全部测试**

```bash
uv run pytest tests/ -v
```

Expected: 148 passed.

- [ ] **Step 2: 验证 import 链路**

```bash
uv run python -c "
from bilianalysis.config.model import AnalysisSection
from bilianalysis.utils.async_utils import safe_run_async
a = AnalysisSection(engine='spark', spark_remote='sc://x:15002', webhdfs_url='http://x:9870')
assert a.webhdfs_url == 'http://x:9870'
print('Config OK')
print('safe_run_async OK')
"
```

- [ ] **Step 3: 验证启动日志**

```bash
uv run bilianalysis serve --port 8080
# 期望输出:
# [spark] Checking connectivity to sc://192.168.212.134:15002 ...
# [spark] Connected to sc://192.168.212.134:15002
# [spark] HDFS reachable via webhdfs (http://192.168.212.134:9870)
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore: final verification — all tests pass"
```

---

### 改动总览

| 文件 | 操作 | 行数变化 |
|------|------|---------|
| `src/bilianalysis/utils/async_utils.py` | 新建 | +35 |
| `src/bilianalysis/config/model.py` | 修改 | -2/+1 |
| `src/bilianalysis/engine/spark_engine.py` | 重写 | ~-200 |
| `src/bilianalysis/engine/pandas_engine.py` | 修改 | ~-25 |
| `src/bilianalysis/engine/__init__.py` | 修改 | 2 处 |
| `app/api/app.py` | 修改 | ~-15/+20 |
| `config.yaml` | 修改 | ~-2/+2 |
| `config.example.yaml` | 修改 | ~-2/+2 |
