# 调度系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现调度系统——Task 注册表 + PipelineRunner + cron 定时 + CLI（Typer + rich）

**Architecture:** 核心调度逻辑在 `src/bilianalysis/scheduler/`（纯库），CLI 在 `app/cli/`（薄层），通过 Task 抽象 + 装饰器注册表将 5 个分析步骤解耦为可组合的流水线。

**Tech Stack:** schedule, typer, rich, fastapi, uvicorn

---

## 文件结构

```
新建:
├── app/cli/
│   ├── __init__.py               # Typer app 入口
│   ├── schedule_cmd.py           # schedule 子命令组
│   └── utils.py                  # rich 渲染工具
├── src/bilianalysis/scheduler/
│   ├── __init__.py               # 公开 API
│   ├── task.py                   # Task ABC + TaskResult + TaskContext
│   ├── registry.py              # register 装饰器 + get_task / list_tasks
│   ├── models.py                # RunRecord
│   ├── runner.py                # PipelineRunner
│   ├── cron_service.py          # schedule 常驻进程 + FastAPI
│   └── builtins/
│       ├── __init__.py
│       ├── crawl_task.py
│       ├── clean_task.py
│       ├── stats_task.py
│       ├── cluster_task.py
│       └── predict_task.py
├── tests/test_scheduler.py       # ~15 个测试

修改:
├── src/bilianalysis/config/model.py    # 新增 SchedulerConfig + PipelineConfig
├── pyproject.toml                      # 新增依赖 + [project.scripts]
```

**Design:** PipelineConfig 和 SchedulerConfig 放入 `config/model.py`（遵循现有模式），RunRecord 放入 `scheduler/models.py`。引擎实例惰性创建，由 PipelineRunner 的 finally 块清理。

---

### Task 1: 添加依赖 + 扩展配置模型

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/bilianalysis/config/model.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: 添加新依赖**

Run:
```bash
uv add schedule typer rich
uv add fastapi uvicorn
```

- [ ] **Step 2: 验证依赖安装**

Run: `uv run python -c "import schedule, typer, rich, fastapi, uvicorn; print('ok')"`
Expected: `ok`

- [ ] **Step 3: 扩展 config/model.py**

在 `src/bilianalysis/config/model.py` 中追加：

```python
class PipelineConfig(BaseModel):
    """单条流水线配置"""
    schedule: str = ""                         # cron 表达式，空字符串表示仅手动
    steps: list[str] = []                      # ["crawl", "clean_data"]
    step_failure: Literal["stop", "skip", "retry"] = "stop"
    max_retries: int = 0                       # 流水线级重试（仅 retry 模式）


class SchedulerConfig(BaseModel):
    """调度配置节"""
    pipelines: dict[str, PipelineConfig] = {}
```

在 `AppConfig` 中追加一行：

```python
class AppConfig(BaseModel):
    """应用根配置"""
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
    scheduler: SchedulerConfig = SchedulerConfig()  # 新增
```

- [ ] **Step 4: 写配置模型测试**

在 `tests/test_scheduler.py` 中写入：

```python
"""测试调度系统。"""
import pytest
import yaml
from bilianalysis.config.model import AppConfig, SchedulerConfig, PipelineConfig


class TestSchedulerConfig:
    def test_default_config(self):
        cfg = SchedulerConfig()
        assert cfg.pipelines == {}

    def test_pipeline_config_defaults(self):
        pc = PipelineConfig()
        assert pc.schedule == ""
        assert pc.steps == []
        assert pc.step_failure == "stop"
        assert pc.max_retries == 0

    def test_yaml_round_trip(self):
        yaml_str = """
scheduler:
  pipelines:
    full:
      schedule: "0 12 * * 6"
      steps:
        - crawl
        - clean_data
        - statistics
        - clustering
        - prediction
      step_failure: stop
      max_retries: 0
    quick:
      schedule: "0 8 * * *"
      steps:
        - crawl
        - statistics
      step_failure: skip
      max_retries: 1
"""
        data = yaml.safe_load(yaml_str)
        cfg = AppConfig(**data)
        assert len(cfg.scheduler.pipelines) == 2
        full = cfg.scheduler.pipelines["full"]
        assert full.schedule == "0 12 * * 6"
        assert len(full.steps) == 5
        assert full.step_failure == "stop"
        quick = cfg.scheduler.pipelines["quick"]
        assert quick.step_failure == "skip"
        assert quick.max_retries == 1
```

- [ ] **Step 5: 运行测试验证**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/bilianalysis/config/model.py tests/test_scheduler.py
git commit -m "feat: add scheduler config models + dependencies"
```

---

### Task 2: Task ABC + 注册表

**Files:**
- Create: `src/bilianalysis/scheduler/__init__.py`
- Create: `src/bilianalysis/scheduler/task.py`
- Create: `src/bilianalysis/scheduler/registry.py`
- Modify: `tests/test_scheduler.py` (追加测试)

- [ ] **Step 1: 创建 scheduler 包占位**

```python
# src/bilianalysis/scheduler/__init__.py
"""调度系统——Task 注册表 + PipelineRunner + cron 服务。"""
```

- [ ] **Step 2: 写 task.py**

```python
# src/bilianalysis/scheduler/task.py
"""Task 抽象接口与上下文模型。"""
import time
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine


class TaskResult(BaseModel):
    """单个 Task 的执行结果。"""
    task_name: str
    status: Literal["success", "failed", "skipped"]
    duration_seconds: float
    output: dict = {}
    error: str | None = None


class TaskContext(BaseModel):
    """Task 执行上下文——携带配置、引擎、上游结果。"""
    model_config = {"arbitrary_types_allowed": True}

    config: AppConfig
    engine: AnalysisEngine | None = None
    previous: dict[str, TaskResult] = {}
    shared: dict = {}


class Task(ABC):
    """Task 抽象基类。子类必须设置 name 并实现 async run()。"""
    name: str

    @abstractmethod
    async def run(self, ctx: TaskContext) -> TaskResult:
        """执行任务。内部负责异常捕获，永远不抛异常。"""
        ...
```

- [ ] **Step 3: 写 registry.py**

```python
# src/bilianalysis/scheduler/registry.py
"""Task 注册表——装饰器注册 + 按名查询。"""
from __future__ import annotations

from .task import Task

_registry: dict[str, type[Task]] = {}


def register(name: str):
    """装饰器：将 Task 子类注册到全局注册表。

    Usage:
        @register("crawl")
        class CrawlTask(Task):
            ...
    """
    def decorator(cls: type[Task]) -> type[Task]:
        if name in _registry:
            raise ValueError(f"Task '{name}' is already registered")
        _registry[name] = cls
        return cls
    return decorator


def get_task(name: str) -> type[Task]:
    """按名获取 Task 类。不存在时抛出 KeyError。"""
    if name not in _registry:
        raise KeyError(f"Task '{name}' not found. Available: {list(_registry)}")
    return _registry[name]


def list_tasks() -> list[str]:
    """列出所有已注册的 Task 名称。"""
    return sorted(_registry.keys())


def clear_registry() -> None:
    """清空注册表（仅用于测试）。"""
    _registry.clear()
```

- [ ] **Step 4: 在 tests/test_scheduler.py 中追加测试**

追加：

```python
from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register, get_task, list_tasks, clear_registry


class TestTaskABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Task()

    def test_concrete_task_instantiable(self):
        @register("_test_dummy")
        class DummyTask(Task):
            name = "_test_dummy"
            async def run(self, ctx):
                return TaskResult(task_name="dummy", status="success", duration_seconds=0)

        task = DummyTask()
        assert task.name == "_test_dummy"
        clear_registry()

    def test_task_result_model(self):
        result = TaskResult(task_name="crawl", status="success", duration_seconds=1.5,
                            output={"crawled": 3})
        assert result.task_name == "crawl"
        assert result.output["crawled"] == 3
        assert result.error is None

    def test_task_result_failed(self):
        result = TaskResult(task_name="crawl", status="failed", duration_seconds=0.2,
                            error="Connection timeout")
        assert result.status == "failed"
        assert "timeout" in result.error


class TestRegistry:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    def test_register_and_get(self):
        @register("_test_crawl")
        class TestCrawlTask(Task):
            name = "_test_crawl"
            async def run(self, ctx):
                return TaskResult(task_name="crawl", status="success", duration_seconds=0)

        cls = get_task("_test_crawl")
        assert cls is TestCrawlTask

    def test_get_missing_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_task("nonexistent")

    def test_list_tasks_sorted(self):
        @register("_test_b")
        class TaskB(Task):
            name = "_test_b"
            async def run(self, ctx):
                return TaskResult(task_name="b", status="success", duration_seconds=0)

        @register("_test_a")
        class TaskA(Task):
            name = "_test_a"
            async def run(self, ctx):
                return TaskResult(task_name="a", status="success", duration_seconds=0)

        names = list_tasks()
        assert names == ["_test_a", "_test_b"]
```

- [ ] **Step 5: 运行测试**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: 10 PASS (3 config + 4 task ABC + 3 registry)

- [ ] **Step 6: Commit**

```bash
git add src/bilianalysis/scheduler/ tests/test_scheduler.py
git commit -m "feat: add Task ABC and registry with decorator"
```

---

### Task 3: RunRecord + PipelineRunner

**Files:**
- Create: `src/bilianalysis/scheduler/models.py`
- Create: `src/bilianalysis/scheduler/runner.py`
- Modify: `tests/test_scheduler.py` (追加 tests)

- [ ] **Step 1: 写 models.py**

```python
# src/bilianalysis/scheduler/models.py
"""调度系统运行时模型。"""
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from bilianalysis.scheduler.task import TaskResult


class RunRecord(BaseModel):
    """一次流水线执行记录。"""
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    pipeline: str
    trigger: Literal["cron", "manual"]
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: Literal["running", "success", "failed"] = "running"
    step_results: list[TaskResult] = []
```

- [ ] **Step 2: 写 runner.py**

```python
# src/bilianalysis/scheduler/runner.py
"""PipelineRunner——按序执行 Task 列表。"""
import time
from datetime import datetime, timezone

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.task import TaskContext, TaskResult
from bilianalysis.scheduler.registry import get_task
from bilianalysis.scheduler.models import RunRecord


class PipelineRunner:
    """流水线执行器。惰性创建引擎，finally 块清理。"""

    def __init__(self, config: AppConfig):
        self._config = config
        self._engine: AnalysisEngine | None = None

    def _ensure_engine(self) -> AnalysisEngine:
        """惰性创建分析引擎（Pandas 或 Spark）。"""
        if self._engine is None:
            from bilianalysis.engine import create_engine
            self._engine = create_engine(self._config)
        return self._engine

    async def run(self, name: str, trigger: str = "manual") -> RunRecord:
        """执行一条流水线。"""
        pipeline = self._config.scheduler.pipelines[name]
        record = RunRecord(pipeline=name, trigger=trigger)
        ctx = TaskContext(config=self._config)

        try:
            for step_name in pipeline.steps:
                task_cls = get_task(step_name)
                task = task_cls()

                # 惰性注入引擎
                if ctx.engine is None:
                    ctx.engine = self._ensure_engine()

                result = await task.run(ctx)
                ctx.previous[step_name] = result
                record.step_results.append(result)

                if result.status == "failed":
                    if pipeline.step_failure == "stop":
                        break
                    elif pipeline.step_failure == "retry":
                        success = False
                        for _ in range(pipeline.max_retries):
                            result = await task.run(ctx)
                            ctx.previous[step_name] = result
                            # replace last result in record
                            record.step_results[-1] = result
                            if result.status == "success":
                                success = True
                                break
                        if not success:
                            break
                    # "skip" → continue to next step

            # 判断整体状态
            all_success = all(
                r.status in ("success", "skipped") for r in record.step_results
            )
            record.status = "success" if all_success else "failed"
        except Exception as exc:
            record.status = "failed"
            record.step_results.append(TaskResult(
                task_name="pipeline", status="failed",
                duration_seconds=0, error=str(exc),
            ))
        finally:
            record.finished_at = datetime.now(timezone.utc)
            # 清理 Spark 引擎
            if self._engine is not None and hasattr(self._engine, "_spark"):
                try:
                    self._engine._spark.stop()
                except Exception:
                    pass

        return record
```

- [ ] **Step 3: 在 tests/test_scheduler.py 中追加 PipelineRunner 测试**

追加：

```python
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.config.model import AppConfig, SchedulerConfig, PipelineConfig


# ——— PipelineRunner 测试用 mock task ———
class _MockSuccessTask(Task):
    name = "_mock_success"
    async def run(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(task_name=self.name, status="success", duration_seconds=0.1,
                          output={"value": 42})

class _MockFailTask(Task):
    name = "_mock_fail"
    async def run(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(task_name=self.name, status="failed", duration_seconds=0.1,
                          error="mock error")

class _MockFlakyTask:
    """第三次才成功的 task。"""
    def __init__(self):
        self._attempts = 0

    async def run(self, ctx: TaskContext) -> TaskResult:
        self._attempts += 1
        if self._attempts < 3:
            return TaskResult(task_name="_mock_flaky", status="failed",
                              duration_seconds=0.1, error=f"attempt {self._attempts}")
        return TaskResult(task_name="_mock_flaky", status="success", duration_seconds=0.1)


class TestRunRecord:
    def test_run_record_defaults(self):
        record = RunRecord(pipeline="full", trigger="manual")
        assert record.status == "running"
        assert record.pipeline == "full"
        assert len(record.run_id) == 12
        assert record.finished_at is None

    def test_run_record_completed(self):
        record = RunRecord(pipeline="quick", trigger="cron")
        record.status = "success"
        record.finished_at = datetime.now(timezone.utc)
        assert record.status == "success"


class TestPipelineRunner:
    def setup_method(self):
        clear_registry()
        # 注册 mock tasks
        register("_mock_success")(_MockSuccessTask)
        register("_mock_fail")(_MockFailTask)

    def teardown_method(self):
        clear_registry()

    def _make_config(self, steps, step_failure="stop", max_retries=0):
        return AppConfig(
            scheduler=SchedulerConfig(
                pipelines={
                    "test": PipelineConfig(
                        steps=steps,
                        step_failure=step_failure,
                        max_retries=max_retries,
                    )
                }
            )
        )

    @pytest.mark.asyncio
    async def test_all_success(self):
        config = self._make_config(["_mock_success", "_mock_success"])
        runner = PipelineRunner(config)
        record = await runner.run("test")
        assert record.status == "success"
        assert len(record.step_results) == 2
        assert all(r.status == "success" for r in record.step_results)

    @pytest.mark.asyncio
    async def test_stop_on_failure(self):
        config = self._make_config(["_mock_success", "_mock_fail", "_mock_success"],
                                   step_failure="stop")
        runner = PipelineRunner(config)
        record = await runner.run("test")
        assert record.status == "failed"
        # 第一个成功，第二个失败，第三个未执行
        assert len(record.step_results) == 2
        assert record.step_results[0].status == "success"
        assert record.step_results[1].status == "failed"

    @pytest.mark.asyncio
    async def test_skip_on_failure(self):
        config = self._make_config(["_mock_success", "_mock_fail", "_mock_success"],
                                   step_failure="skip")
        runner = PipelineRunner(config)
        record = await runner.run("test")
        # skip 模式下，失败的步骤跳过，后续继续
        assert len(record.step_results) == 3
        assert record.step_results[0].status == "success"
        assert record.step_results[1].status == "failed"
        assert record.step_results[2].status == "success"
        # 整体仍为 failed（因为有步骤失败）
        assert record.status == "failed"

    @pytest.mark.asyncio
    async def test_missing_pipeline_raises_keyerror(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        runner = PipelineRunner(config)
        with pytest.raises(KeyError):
            await runner.run("nonexistent")
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: 16 PASS (10 prior + 2 RunRecord + 4 runner)

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/scheduler/models.py src/bilianalysis/scheduler/runner.py tests/test_scheduler.py
git commit -m "feat: add PipelineRunner with stop/skip/retry strategies"
```

---

### Task 4: 五个内置 Task

**Files:**
- Create: `src/bilianalysis/scheduler/builtins/__init__.py`
- Create: `src/bilianalysis/scheduler/builtins/crawl_task.py`
- Create: `src/bilianalysis/scheduler/builtins/clean_task.py`
- Create: `src/bilianalysis/scheduler/builtins/stats_task.py`
- Create: `src/bilianalysis/scheduler/builtins/cluster_task.py`
- Create: `src/bilianalysis/scheduler/builtins/predict_task.py`
- Modify: `tests/test_scheduler.py` (追加 test)

- [ ] **Step 1: 创建 builtins/__init__.py**

```python
# src/bilianalysis/scheduler/builtins/__init__.py
"""内置 Task 实现——导入即注册。"""
from .crawl_task import CrawlTask        # noqa: F401
from .clean_task import CleanDataTask     # noqa: F401
from .stats_task import StatisticsTask    # noqa: F401
from .cluster_task import ClusteringTask  # noqa: F401
from .predict_task import PredictionTask  # noqa: F401
```

- [ ] **Step 2: 写 crawl_task.py**

```python
# src/bilianalysis/scheduler/builtins/crawl_task.py
"""爬虫 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


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
                output={
                    "crawled": report.crawled,
                    "skipped": report.skipped,
                    "failed": report.failed,
                    "total": report.total,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="crawl", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 3: 写 clean_task.py**

```python
# src/bilianalysis/scheduler/builtins/clean_task.py
"""数据清洗 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("clean_data")
class CleanDataTask(Task):
    name = "clean_data"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = await ctx.engine.clean_data()
            return TaskResult(
                task_name="clean_data", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "total_weeks": report.total_weeks,
                    "total_videos": report.total_videos,
                    "duplicates_dropped": report.duplicates_dropped,
                    "outliers_flagged": report.outliers_flagged,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="clean_data", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 4: 写 stats_task.py**

```python
# src/bilianalysis/scheduler/builtins/stats_task.py
"""统计分析 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("statistics")
class StatisticsTask(Task):
    name = "statistics"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.statistics()
            return TaskResult(
                task_name="statistics", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "total_videos": report.overall.total_videos,
                    "avg_view": report.overall.avg_view,
                    "avg_like_rate": report.overall.avg_like_rate,
                    "category_count": len(report.by_category),
                    "creator_count": len(report.by_creator),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="statistics", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 5: 写 cluster_task.py**

```python
# src/bilianalysis/scheduler/builtins/cluster_task.py
"""聚类分析 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("clustering")
class ClusteringTask(Task):
    name = "clustering"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.clustering()
            return TaskResult(
                task_name="clustering", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "k": report.clusters.k,
                    "silhouette_score": report.clusters.silhouette_score,
                    "cluster_count": len(report.clusters.clusters),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="clustering", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 6: 写 predict_task.py**

```python
# src/bilianalysis/scheduler/builtins/predict_task.py
"""回归预测 Task。"""
import time

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register


@register("prediction")
class PredictionTask(Task):
    name = "prediction"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = ctx.engine.prediction()
            return TaskResult(
                task_name="prediction", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "view_r2": report.view_predict.r2_score,
                    "view_mae": report.view_predict.mae,
                    "like_r2": report.like_predict.r2_score,
                    "like_mae": report.like_predict.mae,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="prediction", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 7: 验证 builtins 导入即注册**

Run: `uv run python -c "from bilianalysis.scheduler.builtins import *; from bilianalysis.scheduler.registry import list_tasks; print(list_tasks())"`
Expected: `['clean_data', 'clustering', 'crawl', 'prediction', 'statistics']`

- [ ] **Step 8: 在 tests/test_scheduler.py 追加 crawled task 测试**

追加：

```python
from unittest.mock import AsyncMock, patch


class TestBuiltinTasks:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    @pytest.mark.asyncio
    async def test_crawl_task_success(self):
        from bilianalysis.scheduler.builtins.crawl_task import CrawlTask
        from bilianalysis.crawler import CrawlReport

        task = CrawlTask()
        ctx = TaskContext(
            config=AppConfig(scheduler=SchedulerConfig(pipelines={})),
        )

        mock_report = CrawlReport(
            total=50, crawled=3, skipped=47, failed=0,
            failed_weeks={}, duration_seconds=2.5,
        )
        with patch("bilianalysis.scheduler.builtins.crawl_task.CrawlRunner",
                   new_callable=AsyncMock) as mock_runner:
            mock_runner.return_value = mock_report
            result = await task.run(ctx)

        assert result.status == "success"
        assert result.output["crawled"] == 3
        assert result.output["skipped"] == 47

    @pytest.mark.asyncio
    async def test_crawl_task_failure(self):
        from bilianalysis.scheduler.builtins.crawl_task import CrawlTask

        task = CrawlTask()
        ctx = TaskContext(
            config=AppConfig(scheduler=SchedulerConfig(pipelines={})),
        )
        with patch("bilianalysis.scheduler.builtins.crawl_task.CrawlRunner",
                   new_callable=AsyncMock) as mock_runner:
            mock_runner.side_effect = RuntimeError("network error")
            result = await task.run(ctx)

        assert result.status == "failed"
        assert "network error" in result.error
```

- [ ] **Step 9: 运行全部测试**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: 18 PASS (16 prior + 2 builtin)

- [ ] **Step 10: Commit**

```bash
git add src/bilianalysis/scheduler/builtins/ tests/test_scheduler.py
git commit -m "feat: add 5 builtin tasks (crawl/clean/stats/cluster/predict)"
```

---

### Task 5: Cron 服务（常驻进程 + 定时触发）

**Files:**
- Create: `src/bilianalysis/scheduler/cron_service.py`
- Modify: `src/bilianalysis/scheduler/__init__.py`
- Modify: `tests/test_scheduler.py` (追加 tests)

- [ ] **Step 1: 写 cron_service.py**

```python
# src/bilianalysis/scheduler/cron_service.py
"""常驻调度服务——schedule 定时 + FastAPI 手动触发。"""
import asyncio
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

import schedule
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.models import RunRecord

logger = logging.getLogger("bilianalysis.scheduler")


class CronService:
    """常驻调度服务。

    主线程跑 FastAPI + uvicorn，后台线程轮询 schedule 库。
    触发时通过 run_coroutine_threadsafe 提交到 event loop。
    """

    def __init__(self, config: AppConfig, max_history: int = 100):
        self.config = config
        self.runner = PipelineRunner(config)
        self._history: deque[RunRecord] = deque(maxlen=max_history)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    # ── schedule 集成 ──

    def _setup_cron_jobs(self) -> None:
        """根据配置注册所有 cron 定时任务。"""
        schedule.clear()
        for name, pipeline in self.config.scheduler.pipelines.items():
            if pipeline.schedule:
                schedule.every().day.at("00:00").do(lambda: None)  # dummy
                # schedule 不支持标准 cron 语法，用其 DSL 替代
                self._register_schedule_job(name, pipeline.schedule)
                logger.info("Registered cron: %s -> %s", name, pipeline.schedule)

    def _register_schedule_job(self, name: str, cron_expr: str) -> None:
        """将 cron 表达式转换为 schedule 库的 API 调用。"""
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning("Invalid cron expression for pipeline '%s': %s", name, cron_expr)
            return

        minute, hour, dom, month, dow = parts
        job = schedule.every()

        if minute == "*" and hour == "*":
            # 不支持太频繁的，跳过
            logger.warning("Too frequent schedule for '%s', skipping", name)
            return

        if dow != "*":
            # 按星期
            day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if "," in dow:
                days = [int(d) for d in dow.split(",")]
                dow_str = ",".join(day_names[d] for d in days if 0 <= d <= 6)
                getattr(job, dow_str) if "," not in dow_str else None
            else:
                d = int(dow)
                if 0 <= d <= 6:
                    job = getattr(job, day_names[d])
        else:
            job = job.day

        if hour != "*":
            job = job.at(f"{hour.zfill(2)}:{minute.zfill(2)}")

        job.do(lambda n=name: self._trigger_cron(n))

    def _trigger_cron(self, name: str) -> None:
        """cron 触发回调——从后台线程提交到 event loop。"""
        if self._loop is None:
            logger.error("Event loop not set, cannot trigger %s", name)
            return
        asyncio.run_coroutine_threadsafe(self._execute_pipeline(name, "cron"), self._loop)

    async def _execute_pipeline(self, name: str, trigger: str) -> RunRecord:
        """执行流水线并记录历史。"""
        logger.info("Pipeline '%s' triggered by %s", name, trigger)
        record = await self.runner.run(name, trigger=trigger)
        self._history.append(record)
        status_icon = "✓" if record.status == "success" else "✗"
        logger.info("%s Pipeline '%s' completed: %s in %.1fs",
                     status_icon, name, record.status,
                     (record.finished_at - record.started_at).total_seconds()
                     if record.finished_at else 0)
        return record

    # ── FastAPI app ──

    def create_app(self) -> FastAPI:
        """创建 FastAPI 应用（serve 模式使用）。"""
        app = FastAPI(title="BiliAnalysis Scheduler", version="0.1.0")
        service = self  # 闭包引用

        @app.get("/health")
        async def health():
            return {"status": "ok", "pipelines": list(self.config.scheduler.pipelines.keys())}

        @app.get("/pipelines")
        async def list_pipelines():
            result = {}
            for name, pl in self.config.scheduler.pipelines.items():
                result[name] = {
                    "schedule": pl.schedule,
                    "steps": pl.steps,
                    "step_failure": pl.step_failure,
                }
            return result

        @app.get("/pipelines/{name}/runs")
        async def pipeline_runs(name: str, limit: int = 20):
            if name not in self.config.scheduler.pipelines:
                raise HTTPException(404, f"Pipeline '{name}' not found")
            runs = [r for r in self._history if r.pipeline == name]
            return runs[-limit:]

        @app.post("/pipelines/{name}/run")
        async def trigger_pipeline(name: str):
            if name not in self.config.scheduler.pipelines:
                raise HTTPException(404, f"Pipeline '{name}' not found")
            # 后台执行，不阻塞请求
            task = asyncio.create_task(service._execute_pipeline(name, "manual"))
            record = RunRecord(pipeline=name, trigger="manual")
            service._history.append(record)
            return JSONResponse(
                status_code=202,
                content={"run_id": record.run_id, "pipeline": name, "status": "accepted"},
            )

        return app

    # ── 启动 / 停止 ──

    def start(self, port: int = 8080) -> None:
        """阻塞式启动 serve 模式。"""
        import uvicorn

        self._running = True
        self._setup_cron_jobs()

        # 后台线程：schedule 轮询
        def _run_schedule():
            while self._running:
                schedule.run_pending()
                time.sleep(1)

        thread = threading.Thread(target=_run_schedule, daemon=True)
        thread.start()

        # 主线程：FastAPI
        self._loop = asyncio.get_event_loop()
        app = self.create_app()
        logger.info("Scheduler started on http://127.0.0.1:%d", port)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

    def stop(self) -> None:
        """停止服务。"""
        self._running = False
        schedule.clear()
```

- [ ] **Step 2: 更新 scheduler/__init__.py 公开 API**

```python
# src/bilianalysis/scheduler/__init__.py
"""调度系统——Task 注册表 + PipelineRunner + cron 服务。"""
from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register, get_task, list_tasks
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.cron_service import CronService

__all__ = [
    "Task", "TaskResult", "TaskContext",
    "register", "get_task", "list_tasks",
    "PipelineRunner", "RunRecord", "CronService",
]
```

- [ ] **Step 3: 在 tests/test_scheduler.py 追加 cron service 测试**

追加：

```python
from bilianalysis.scheduler.cron_service import CronService


class TestCronService:
    @pytest.mark.asyncio
    async def test_create_app_returns_fastapi(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        service = CronService(config)
        app = service.create_app()
        assert app.title == "BiliAnalysis Scheduler"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        config = AppConfig(scheduler=SchedulerConfig(
            pipelines={"full": PipelineConfig(steps=["crawl"])}
        ))
        service = CronService(config)
        app = service.create_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "full" in resp.json()["pipelines"]

    @pytest.mark.asyncio
    async def test_list_pipelines(self):
        from fastapi.testclient import TestClient

        config = AppConfig(scheduler=SchedulerConfig(
            pipelines={
                "full": PipelineConfig(schedule="0 12 * * 6", steps=["crawl"]),
            }
        ))
        service = CronService(config)
        app = service.create_app()
        client = TestClient(app)
        resp = client.get("/pipelines")
        assert resp.status_code == 200
        data = resp.json()
        assert data["full"]["schedule"] == "0 12 * * 6"

    def test_trigger_nonexistent_pipeline_404(self):
        from fastapi.testclient import TestClient

        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        service = CronService(config)
        app = service.create_app()
        client = TestClient(app)
        resp = client.post("/pipelines/nonexistent/run")
        assert resp.status_code == 404
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: 22 PASS (18 prior + 4 cron service)

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/scheduler/cron_service.py src/bilianalysis/scheduler/__init__.py tests/test_scheduler.py
git commit -m "feat: add CronService with schedule + FastAPI endpoints"
```

---

### Task 6: CLI + Rich 美化

**Files:**
- Create: `app/cli/__init__.py`
- Create: `app/cli/utils.py`
- Create: `app/cli/schedule_cmd.py`
- Modify: `pyproject.toml` (add [project.scripts])

- [ ] **Step 1: 配置 pyproject.toml 入口点**

在 `pyproject.toml` 末尾追加：

```toml
[project.scripts]
bilianalysis = "app.cli:app"
```

- [ ] **Step 2: 写 app/cli/utils.py**

```python
# app/cli/utils.py
"""Rich 终端渲染工具。"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich import box

console = Console()


def make_task_table(task_infos: list[dict]) -> Table:
    """渲染 Task 列表表格。"""
    table = Table(title="Available Tasks", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    for info in task_infos:
        table.add_row(info["name"], info.get("description", ""))
    return table


def make_pipeline_table(pipelines: dict) -> Table:
    """渲染 Pipeline 列表表格。"""
    table = Table(title="Pipelines", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule", style="yellow")
    table.add_column("Steps", style="green")
    for name, pl in pipelines.items():
        schedule_str = pl.schedule or "manual only"
        steps_str = " -> ".join(pl.steps[:5])
        if len(pl.steps) > 5:
            steps_str += f" ...(+{len(pl.steps) - 5})"
        table.add_row(name, schedule_str, steps_str)
    return table


def make_progress_panel(pipeline_name: str, steps: list[str], trigger: str = "manual") -> Panel:
    """渲染流水线进度面板标题。"""
    steps_str = " → ".join(steps)
    return Panel(
        f"Pipeline: [bold cyan]{pipeline_name}[/bold cyan]     trigger: {trigger}\n"
        f"Steps: {steps_str}",
        box=box.ROUNDED,
    )


def make_serve_banner(config) -> Panel:
    """渲染 serve 启动画面。"""
    lines = [
        "[bold cyan]BiliAnalysis Scheduler v0.1.0[/bold cyan]",
        "─" * 45,
        f"Engine: [yellow]{config.analysis.engine}[/yellow]",
        f"Pipelines: [green]{len(config.scheduler.pipelines)}[/green]",
        "",
    ]
    for name, pl in config.scheduler.pipelines.items():
        cron_hint = pl.schedule or "manual only"
        steps_short = "→".join(pl.steps[:5])
        lines.append(f"  [cyan]{name:<8}[/cyan] {cron_hint:<16} {steps_short}")
    return Panel("\n".join(lines), box=box.ROUNDED, title="🚀 Scheduler Started")
```

- [ ] **Step 3: 写 app/cli/__init__.py**

```python
# app/cli/__init__.py
"""BiliAnalysis CLI——统一命令行入口。"""
import typer

app = typer.Typer(name="bilianalysis", help="Bilibili 每周必看数据分析平台")


# 延迟导入子命令，避免启动时加载所有依赖
@app.callback()
def _main():
    pass


def _register_schedule():
    """延迟注册 schedule 子命令。"""
    from app.cli.schedule_cmd import schedule_app
    app.add_typer(schedule_app, name="schedule", help="定时调度管理")


_register_schedule()
```

- [ ] **Step 4: 写 app/cli/schedule_cmd.py**

```python
# app/cli/schedule_cmd.py
"""schedule 子命令组——run / serve / list / test。"""
import asyncio
import sys
from pathlib import Path

import typer
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from bilianalysis.config import load_config
from bilianalysis.scheduler.registry import list_tasks, get_task
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.cron_service import CronService
from app.cli.utils import (
    console, make_task_table, make_pipeline_table,
    make_progress_panel, make_serve_banner,
)

schedule_app = typer.Typer(name="schedule", help="定时调度管理")

# Task 描述映射（用于 list 命令）
_TASK_DESCRIPTIONS = {
    "crawl": "爬取B站每周必看原始数据",
    "clean_data": "清洗数据 -> 5 张 Parquet 表",
    "statistics": "统计分析（overall/分区/UP/周趋势）",
    "clustering": "KMeans 聚类（k=3）",
    "prediction": "线性回归预测（播放量/点赞量）",
}


@schedule_app.command("list")
def list_cmd(
        config_path: str = typer.Option("config.yaml", "--config", "-c", help="配置文件路径"),
):
    """列出所有可用的 Task 和 Pipeline。"""
    from bilianalysis.scheduler.builtins import *  # noqa: F401  # 触发注册

    config = load_config(config_path)

    # Task 表格
    task_infos = [
        {"name": name, "description": _TASK_DESCRIPTIONS.get(name, "")}
        for name in list_tasks()
    ]
    console.print(make_task_table(task_infos))

    # Pipeline 表格
    if config.scheduler.pipelines:
        console.print(make_pipeline_table(config.scheduler.pipelines))
    else:
        console.print("[dim]No pipelines configured in config.yaml[/dim]")


@schedule_app.command("run")
def run_cmd(
        pipeline: str = typer.Option(..., "--pipeline", "-p", help="流水线名称"),
        config_path: str = typer.Option("config.yaml", "--config", "-c", help="配置文件路径"),
):
    """手动触发一次流水线执行。"""
    from bilianalysis.scheduler.builtins import *  # noqa: F401

    config = load_config(config_path)
    if pipeline not in config.scheduler.pipelines:
        console.print(f"[red]Pipeline '{pipeline}' not found in config[/red]")
        raise typer.Exit(1)

    pl = config.scheduler.pipelines[pipeline]
    runner = PipelineRunner(config)

    # Rich 进度展示
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )
    progress_ids = {}
    for step in pl.steps:
        progress_ids[step] = progress.add_task(step, total=None, status="pending")

    async def _run():
        record = await runner.run(pipeline, trigger="manual")
        for i, result in enumerate(record.step_results):
            step = pl.steps[i] if i < len(pl.steps) else "unknown"
            if result.status == "success":
                desc = f"[green]●[/green] {step:<15} {result.duration_seconds:.1f}s"
                if result.output:
                    key_vals = " ".join(f"{k}={v}" for k, v in list(result.output.items())[:3])
                    desc += f"  [dim]{key_vals}[/dim]"
                progress.update(progress_ids.get(step, progress_ids.get(step, 0)),
                                description=desc, completed=True)
            elif result.status == "failed":
                progress.update(progress_ids.get(step, progress_ids.get(step, 0)),
                                description=f"[red]✗[/red] {step:<15} [red]{result.error or 'failed'}[/red]",
                                completed=True)
        return record

    with Live(progress, console=console, refresh_per_second=4):
        record = asyncio.run(_run())

    # Summary
    status_color = "green" if record.status == "success" else "red"
    console.print(f"\n[{status_color}]Pipeline '{pipeline}': {record.status}[/{status_color}] "
                  f"in {record.step_results[-1].duration_seconds if record.step_results else 0:.1f}s")


@schedule_app.command("serve")
def serve_cmd(
        port: int = typer.Option(8080, "--port", "-p", help="API 监听端口"),
        config_path: str = typer.Option("config.yaml", "--config", "-c", help="配置文件路径"),
):
    """启动常驻调度进程（cron 定时 + HTTP API）。"""
    from bilianalysis.scheduler.builtins import *  # noqa: F401

    config = load_config(config_path)
    console.print(make_serve_banner(config))
    console.print(f"\n  API:   [cyan]http://127.0.0.1:{port}[/cyan]")
    console.print(f"  Docs:  [cyan]http://127.0.0.1:{port}/docs[/cyan]\n")

    service = CronService(config)
    try:
        service.start(port=port)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        service.stop()


@schedule_app.command("test")
def test_cmd(
        pipeline: str = typer.Option(..., "--pipeline", "-p", help="流水线名称"),
        config_path: str = typer.Option("config.yaml", "--config", "-c", help="配置文件路径"),
):
    """试跑校验——仅检查配置、导入和步骤名称。"""
    from bilianalysis.scheduler.builtins import *  # noqa: F401

    config = load_config(config_path)
    if pipeline not in config.scheduler.pipelines:
        console.print(f"[red]Pipeline '{pipeline}' not found in config[/red]")
        raise typer.Exit(1)

    pl = config.scheduler.pipelines[pipeline]
    console.print(f"[bold]Checking pipeline: {pipeline}[/bold]")
    for step in pl.steps:
        try:
            get_task(step)
            console.print(f"  [green]✓[/green] {step}")
        except KeyError as e:
            console.print(f"  [red]✗[/red] {step} — {e}")
            raise typer.Exit(1)
    console.print(f"\n[green]All {len(pl.steps)} steps valid.[/green]")
```

- [ ] **Step 5: 验证 CLI 导入**

Run: `uv run python -c "from app.cli import app; print('CLI app loaded')"`
Expected: `CLI app loaded`

- [ ] **Step 6: 验证 schedule list 命令**

Run: `uv run bilianalysis schedule list`
Expected: 表格输出所有 Tasks（crawl/clean_data/statistics/clustering/prediction），无 Pipeline（无 config.yaml）

- [ ] **Step 7: 验证 schedule test 命令**

Run: `uv run bilianalysis schedule test --pipeline full --config config.yaml 2>&1 || true`
Expected: （如 config.yaml 不存在则报错，存在则校验通过）

- [ ] **Step 8: Commit**

```bash
git add app/cli/ pyproject.toml
git commit -m "feat: add CLI with rich output (schedule run/serve/list/test)"
```

---

### Task 7: 最终验证 + E2E 测试

**Files:**
- Modify: `tests/test_scheduler.py` (追加 CLI 测试)

- [ ] **Step 1: 追加 CLI 集成测试**

在 `tests/test_scheduler.py` 末尾追加：

```python
from typer.testing import CliRunner
from app.cli import app as cli_app


class TestCLI:
    def test_list_command_outputs_tasks(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "list"])
        assert result.exit_code == 0
        assert "crawl" in result.stdout
        assert "statistics" in result.stdout

    def test_test_command_valid_pipeline(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_data = {
            "scheduler": {
                "pipelines": {
                    "full": {"steps": ["crawl", "statistics"]}
                }
            }
        }
        config_path.write_text(yaml.dump(config_data))
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "test", "--pipeline", "full",
                                          "--config", str(config_path)])
        assert result.exit_code == 0
        assert "All 2 steps valid" in result.stdout

    def test_test_command_invalid_step(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_data = {
            "scheduler": {
                "pipelines": {
                    "bad": {"steps": ["nonexistent_task"]}
                }
            }
        }
        config_path.write_text(yaml.dump(config_data))
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "test", "--pipeline", "bad",
                                          "--config", str(config_path)])
        assert result.exit_code == 1
```

- [ ] **Step 2: 运行全部测试**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (~79 existing + 25 scheduler = ~104 total)

- [ ] **Step 3: E2E 烟雾测试——手动触发 run 命令**

创建临时配置并跑一次（用 Pandas 引擎 + 模拟数据）：

```bash
uv run python -c "
import json, tempfile, os, yaml
from pathlib import Path

td = tempfile.mkdtemp()
raw = Path(td) / 'raw'
processed = Path(td) / 'processed'
raw.mkdir(parents=True)

# 写测试数据
data = {
    'number': 1,
    'config': {'subject': 'test', 'name': 'test', 'start_time': 1600000000, 'end_time': 1600600000},
    'videos': [{
        'aid': 1, 'bvid': 'BV1', 'title': 'test', 'desc': '', 'duration': 120,
        'pubdate': 1600000000, 'cid': 10, 'pic': '',
        'owner': {'mid': 100, 'name': 'UP', 'face': ''},
        'stat': {'aid': 1, 'view': 1000, 'like': 50, 'coin': 10, 'favorite': 20, 'share': 5, 'reply': 8, 'danmaku': 12},
        'tid': 1, 'tname': '动画',
    }]
}
with open(raw / 'week_001.json', 'w') as f:
    json.dump(data, f)

# 写配置
cfg = {
    'analysis': {'engine': 'pandas'},
    'data': {'raw_dir': str(raw), 'processed_dir': str(processed), 'reports_dir': str(td) + '/reports'},
    'scheduler': {
        'pipelines': {
            'test': {'steps': ['clean_data', 'statistics']}
        }
    }
}
cfg_path = Path(td) / 'config.yaml'
cfg_path.write_text(yaml.dump(cfg))

# 用 API 方式直接跑（绕开 CLI，验证核心流程）
import asyncio
from bilianalysis.config import load_config
from bilianalysis.scheduler import PipelineRunner
from bilianalysis.scheduler.builtins import *

async def main():
    config = load_config(str(cfg_path))
    runner = PipelineRunner(config)
    record = await runner.run('test')
    print(f'Status: {record.status}')
    for r in record.step_results:
        print(f'  {r.task_name}: {r.status} ({r.duration_seconds}s) -> {r.output}')
    assert record.status == 'success', f'Expected success, got {record.status}'

asyncio.run(main())
print('E2E smoke test PASSED')
"
```

Expected: `E2E smoke test PASSED`

- [ ] **Step 4: 最终 Commit**

```bash
git add tests/test_scheduler.py
git commit -m "test: add CLI integration tests and E2E smoke test"
```
