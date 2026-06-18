# 调度系统设计

> **Status:** Draft | **Date:** 2026-06-18

## 1. 概述

为 BiliAnalysis 添加定时调度能力，支持多流水线配置、cron 定时触发、API 手动触发。用 Typer + rich 做 CLI，`schedule` 库做定时引擎，核心逻辑放 `src/bilianalysis/scheduler/`，CLI 放 `app/cli/`。

### 目标

- 定义可复用的 Task 抽象，每个分析步骤为一个 Task
- YAML 配置多条 Pipeline（Task 有序序列），每条可绑定 cron 表达式
- CLI 一键启动常驻调度进程或手动触发
- 输出美观（rich 进度条、面板、表格）
- 调度核心与 CLI 分离，后续可集成到 FastAPI

---

## 2. 架构

```
app/cli/                          src/bilianalysis/scheduler/
────────────────────────────────  ──────────────────────────────────
schedule_cmd.py                   runner.py        PipelineRunner
  ├── run    →────────────────→     run("full") → Task1 → Task2 → ...
  ├── serve  →────────────────→   cron_service.py   schedule 库 + API
  ├── list   →────────────────→   registry.py      列出 tasks/pipelines
  └── test   →────────────────→   task.py          Task ABC

utils.py (rich 渲染)              models.py        SchedulerConfig / RunRecord
                                  builtins/        5 个内置 Task
```

**分层原则：**
- `src/bilianalysis/scheduler/` — 纯库，零 CLI 依赖，可被 CLI / FastAPI / 测试 复用
- `app/cli/` — 薄层，参数解析 + rich 渲染
- `builtins/` — 每个 Task ~30 行，只做参数适配 + 调用现有函数

---

## 3. 核心模型

### 3.1 Task 接口

```python
# scheduler/task.py

class TaskResult(BaseModel):
    task_name: str
    status: Literal["success", "failed", "skipped"]
    duration_seconds: float
    output: dict = {}         # {"crawled": 32, "skipped": 180}
    error: str | None = None

class TaskContext(BaseModel):
    config: AppConfig                             # 完整应用配置
    engine: AnalysisEngine | None = None          # 已创建的引擎实例
    previous: dict[str, TaskResult] = {}          # 上游步骤结果
    shared: dict = {}                             # 流水线共享状态

class Task(ABC):
    name: str

    @abstractmethod
    async def run(self, ctx: TaskContext) -> TaskResult: ...
```

### 3.2 注册表

```python
# scheduler/registry.py

_registry: dict[str, type[Task]] = {}

def register(name: str):
    """装饰器：将 Task 子类注册到全局注册表。"""
    def decorator(cls):
        _registry[name] = cls
        return cls
    return decorator

def get_task(name: str) -> type[Task]: ...
def list_tasks() -> list[str]: ...
```

### 3.3 配置模型

```python
# config/model.py 扩展

class PipelineConfig(BaseModel):
    schedule: str = ""                    # cron 表达式
    steps: list[str] = []                 # ["crawl", "clean_data", ...]
    step_failure: Literal["stop", "skip", "retry"] = "stop"
    max_retries: int = 0                  # 流水线级别重试次数

class SchedulerConfig(BaseModel):
    pipelines: dict[str, PipelineConfig] = {}

class AppConfig(BaseModel):
    # ... 已有字段
    scheduler: SchedulerConfig = SchedulerConfig()    # 新增
```

### 3.4 执行记录

```python
# scheduler/models.py

class RunRecord(BaseModel):
    run_id: str                           # uuid
    pipeline: str                         # "full"
    trigger: Literal["cron", "manual"]
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal["running", "success", "failed"] = "running"
    step_results: list[TaskResult] = []
```

---

## 4. YAML 配置

```yaml
# config.yaml（扩展示例）

crawler:
  mode: concurrent
  concurrency: 5

analysis:
  engine: spark

data:
  raw_dir: data/raw
  processed_dir: data/processed
  reports_dir: data/reports

scheduler:
  pipelines:
    full:
      schedule: "0 12 * * 6"          # 每周六 12:00
      step_failure: stop
      max_retries: 0
      steps:
        - crawl
        - clean_data
        - statistics
        - clustering
        - prediction
    quick:
      schedule: "0 8 * * *"           # 每天 08:00
      step_failure: skip
      max_retries: 1
      steps:
        - crawl
        - statistics
```

---

## 5. PipelineRunner

```python
# scheduler/runner.py

class PipelineRunner:
    def __init__(self, config: AppConfig): ...

    async def run(self, name: str, trigger: str = "manual") -> RunRecord:
        """执行一条流水线。"""
        pipeline = config.scheduler.pipelines[name]
        ctx = TaskContext(config=config)

        for step_name in pipeline.steps:
            task = get_task(step_name)()
            result = await task.run(ctx)
            ctx.previous[step_name] = result

            if result.status == "failed":
                if pipeline.step_failure == "stop":
                    break
                elif pipeline.step_failure == "retry":
                    for attempt in range(pipeline.max_retries):
                        result = await task.run(ctx)
                        if result.status == "success":
                            break

        return RunRecord(...)
```

**关键行为：**
- 按 `steps` 顺序串行执行（当前无并行需求）
- 引擎实例（Pandas/Spark）在首次需要时创建，存入 `ctx.engine`，流水线结束由调用方清理
- `ctx.previous` 允许下游读取上游输出（如 `statistics` 可校验 `clean_data.total_videos > 0`）

---

## 6. 内置 Task

5 个内置 Task，放在 `src/bilianalysis/scheduler/builtins/`：

| Task | 调用 | 关键输出 |
|------|------|----------|
| `crawl` | `CrawlRunner(config.crawler)` | `crawled`, `skipped`, `failed` |
| `clean_data` | `engine.clean_data()` | `total_weeks`, `total_videos`, `duplicates_dropped` |
| `statistics` | `engine.statistics()` | `total_videos`, `avg_view`, `category_count` |
| `clustering` | `engine.clustering()` | `k`, `silhouette_score` |
| `prediction` | `engine.prediction()` | `view_r2`, `like_r2` |

每个 Task 实现模板（`crawl_task.py` 示例）：

```python
@register("crawl")
class CrawlTask(Task):
    name = "crawl"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            from bilianalysis.crawler import CrawlRunner
            report = await CrawlRunner(ctx.config.crawler)
            return TaskResult(
                task_name="crawl", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={"crawled": report.crawled, "skipped": report.skipped,
                        "failed": report.failed},
            )
        except Exception as e:
            return TaskResult(
                task_name="crawl", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(e),
            )
```

---

## 7. CLI 设计

### 7.1 入口

```toml
# pyproject.toml
[project.scripts]
bilianalysis = "app.cli:app"
```

```python
# app/cli/__init__.py
import typer
from app.cli.schedule_cmd import schedule_app

app = typer.Typer(name="bilianalysis")
app.add_typer(schedule_app, name="schedule")
```

### 7.2 子命令

```
bilianalysis schedule run    手动触发流水线
    --pipeline full
    --config config.yaml

bilianalysis schedule serve  常驻进程（cron + HTTP API）
    --port 8080
    --config config.yaml

bilianalysis schedule list   列出所有 task 和 pipeline

bilianalysis schedule test   试跑校验（仅检查配置和导入）
    --pipeline full
```

### 7.3 `serve` 模式

常驻进程启动时：

1. 主线程启动 FastAPI + uvicorn（`uvicorn.run(app, port=...)`）
2. 后台线程跑 `schedule` 轮询，到点时将流水线执行提交到同一个 asyncio event loop
3. `POST /pipelines/{name}/run` 返回 `202 Accepted` + `run_id`，用 `asyncio.create_task` 后台执行
4. 运行历史存内存（`collections.deque`，最多 100 条）
5. 引擎实例在流水线 `finally` 块中清理（SparkSession.stop / 文件句柄）

```
Main Thread                    Background Thread
─────────────────────         ─────────────────────
uvicorn.run()                 schedule.run_pending()
  │                             │ cron trigger
  ├─ FastAPI app                └─→ asyncio.run_coroutine_threadsafe(
  │   ├─ GET  /pipelines               runner.run("full"), loop)
  │   ├─ POST /pipelines/{name}/run
  │   └─ GET  /health
  │
  └─ event loop ←──────────────────────┘
```

API 端点：
| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/pipelines/{name}/run` | 手动触发，返回 202 + run_id |
| `GET` | `/pipelines` | 列出所有流水线配置 |
| `GET` | `/pipelines/{name}/runs` | 执行历史（最近 20 条，分页参数 `?limit=`) |
| `GET` | `/health` | 健康检查 |

---

## 8. CLI 输出（rich 美化）

### `run` — 实时进度

```
╭──────────────────────────────────────────────────────╮
│ Pipeline: full                        trigger: manual │
│ Steps: crawl → clean → stats → cluster → predict      │
╰──────────────────────────────────────────────────────╯

● crawl         ████████████████████  2.3s  crawled=32 skipped=180
● clean_data    ██████████████        1.1s  videos=894 dupes=3
● statistics    ████████              0.4s  avg_view=45231
◌ clustering    ┄┄┄┄┄┄┄┄┄┄          running...
○ prediction    ┄┄┄┄┄┄┄┄┄┄          pending...

Elapsed: 4.2s
```

图例：`●` 成功 `✗` 失败 `◌` 运行中 `○` 等待

### `serve` — 启动画面

```
╭──────────────────────────────────────────────────╮
│  BiliAnalysis Scheduler v0.1.0                    │
│  ────────────────────────────────────────────      │
│  Engine: spark                                     │
│  Pipelines: 2                                      │
│                                                    │
│  full   每周六 12:00  crawl→clean→stats→clust→pred │
│  quick  每天 08:00     crawl→stats                  │
│                                                    │
│  API:   http://127.0.0.1:8080                     │
│  Docs:  http://127.0.0.1:8080/docs                │
│                                                    │
│  ⏳ Next: full → 2026-06-20 12:00:00              │
╰──────────────────────────────────────────────────╯
```

### `list` — 表格

```
Available Tasks:
┌──────────────┬────────────────────────────────────┐
│ Name         │ Description                        │
├──────────────┼────────────────────────────────────┤
│ crawl        │ 爬取B站每周必看原始数据              │
│ clean_data   │ 清洗 → 5 张 Parquet 表             │
│ statistics   │ 统计分析（overall/分区/UP/周）      │
│ clustering   │ KMeans 聚类（k=3）                 │
│ prediction   │ 线性回归预测（播放/点赞）            │
└──────────────┴────────────────────────────────────┘

Pipelines:
┌───────┬──────────────────┬─────────────────────────┐
│ Name  │ Schedule         │ Steps                   │
├───────┼──────────────────┼─────────────────────────┤
│ full  │ 0 12 * * 6 (六)  │ crawl→clean→stats→clust │
│ quick │ 0 8 * * * (每日)  │ crawl→stats              │
└───────┴──────────────────┴─────────────────────────┘
```

---

## 9. 依赖

新增依赖（`pyproject.toml`）：

```toml
dependencies = [
    # ... 已有
    "schedule>=1.2.0",       # 定时调度
    "typer>=0.9.0",          # CLI 框架
    "rich>=13.0.0",          # 终端美化
    "fastapi>=0.115.0",      # serve 模式 HTTP API
    "uvicorn>=0.30.0",       # ASGI server
]
```

---

## 10. 错误处理

### 三级容错

| 级别 | 范围 | 策略 |
|------|------|------|
| L1 | Task 内部 | `crawl` 已有 max_retries=3；其他 Task 操作本地文件，失败直接报错 |
| L2 | Pipeline 步骤 | `step_failure`: `stop` 终止 / `skip` 跳过继续 / `retry` 重试 |
| L3 | 调度器级 | 流水线崩溃不影响下次定时触发，错误记日志 |

### 日志

- 执行日志输出到 `data/logs/scheduler.log`（按天轮转）
- `serve` 模式下终端同步输出 INFO/WARN 级别
- 异常堆栈仅在 `--verbose` 时显示

---

## 11. 文件清单

```
新建:
├── app/cli/
│   ├── __init__.py               # Typer app 入口
│   ├── schedule_cmd.py           # schedule 子命令组 (run/serve/list/test)
│   └── utils.py                  # rich 渲染工具
├── src/bilianalysis/scheduler/
│   ├── __init__.py               # 公开 API
│   ├── task.py                   # Task ABC + TaskResult + TaskContext
│   ├── registry.py              # 注册表 + register 装饰器
│   ├── runner.py                # PipelineRunner
│   ├── models.py                # PipelineConfig + RunRecord + SchedulerConfig
│   ├── cron_service.py          # schedule 常驻进程 (serve 模式)
│   └── builtins/
│       ├── __init__.py
│       ├── crawl_task.py
│       ├── clean_task.py
│       ├── stats_task.py
│       ├── cluster_task.py
│       └── predict_task.py

修改:
├── src/bilianalysis/config/model.py    # 新增 SchedulerConfig + PipelineConfig
├── pyproject.toml                      # 新增依赖 + [project.scripts]
└── tests/                              # 新增 ~15 个测试
```

---

## 12. 测试策略

| 测试类别 | 数量 | 内容 |
|----------|------|------|
| Task 注册表 | 3 | register 装饰器、重复注册、查询 |
| PipelineRunner | 5 | 成功流程、stop/skip/retry 策略、空步骤 |
| 配置模型 | 2 | 默认值、YAML 反序列化 |
| CLI 命令 | 3 | list 输出格式、run 参数校验、test 模式 |
| 内置 Task | 2 | crawl_task 成功/失败 mock |
| 总计 | ~15 | 全 mock，不依赖真实网络/Spark |
