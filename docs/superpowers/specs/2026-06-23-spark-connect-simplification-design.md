# Spark Connect 集成简化设计

**日期**: 2026-06-23
**目标**: 精简 SparkEngine 架构，统一 HDFS 访问方式，消除冗余代码。

## 背景

当前 SparkEngine 有 4 个构造参数、2 个 HDFS 后端（pyarrow + WebHDFS）、硬编码的 `hdfs://` URI 构造逻辑和重复的辅助函数。经过实际验证：
- WebHDFS (9870) 可用
- Spark 服务端通过 `fs.defaultFS` 自行解析 HDFS 路径，客户端不需要拼接 `hdfs://` URI
- `rcmd_reason` 在所有历史数据中都是纯字符串，不存在 `StructType` 分支
  
## 设计

### 配置

```python
class AnalysisSection(BaseModel):
    engine: Literal["pandas", "spark"] = "pandas"
    spark_remote: str | None = None
    webhdfs_url: str | None = None
    spark_ping_timeout: float = 10.0
    spark_ping_retries: int = 3
    spark_ping_retry_delay: float = 60.0
```

去掉 `hdfs_host` 和 `hdfs_port`，新增 `webhdfs_url`。

```yaml
analysis:
  engine: spark
  spark_remote: "sc://192.168.212.134:15002"
  webhdfs_url: "http://192.168.212.134:9870"
```

### SparkEngine

**构造参数**: `(data_config, spark_remote, webhdfs_url)`

**路径常量**（Spark 自行通过 `fs.defaultFS` 解析）:
```python
HDFS_RAW = "/user/hadoop/bilibili/raw"
HDFS_PROCESSED = "/user/hadoop/bilibili/processed"
```

**HDFS 上传**: 仅 WebHDFS。`_sync_raw_to_hdfs()` 在需要时从 `webhdfs_url` 创建 `InsecureClient`。

**去掉**:
- `_hdfs_raw()` / `_hdfs_processed()` — 直接用路径常量
- pyarrow HDFS 后端
- `_extract_tables` 中 `rcmd_reason` StructType 分支 — 始终 null-fill

### 健康检查

- ping Spark Connect → 重试 N 次 → 全部失败 `sys.exit(1)`
- ping WebHDFS (`client.status("/")`) → 失败 WARNING，服务器继续

### 数据流

```
clean_data:
  _sync_raw_to_hdfs()        → WebHDFS 上传缺失文件
  spark.read.json(HDFS_RAW)  → option("multiline","true")
  _extract_tables()           → rcmd_reason 固定 null
  清洗 → df.write.parquet(HDFS_PROCESSED)

statistics / clustering / prediction:
  _ensure_processed()        → 探测 HDFS_PROCESSED
  spark.read.parquet(...)     → 计算 → 返回报告
```

### 辅助函数

`_safe_run_async` 从两个引擎文件中提取为 `src/bilianalysis/utils/async_utils.py` 中的公共函数。

### API 引擎生命周期

`get_engine()` 使用模块级单例，健康检查复用同一个实例，避免创建孤儿 SparkSession。

## 验证

```bash
uv run pytest tests/ -v          # 全部测试通过
uv run bilianalysis serve --port 8080  # 启动正常，健康检查输出清晰
```
