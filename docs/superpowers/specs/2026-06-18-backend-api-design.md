# FastAPI 后端 API 设计

> **Status:** Draft | **Date:** 2026-06-18

## 1. 概述

为 BiliAnalysis 构建运营级后端 API，提供数据查询、任务触发、配置管理、执行历史等功能。API 层放在 `app/api/`，与 `app/cli/` 共享 `src/bilianalysis/` 库。

### 目标

- RESTful API 暴露爬虫、分析、任务调度三大能力
- 异步任务触发 + 执行历史轮询
- 运行时配置管理 + 可选持久化到 YAML
- 数据优先读 `reports/` JSON，不存在时回退引擎实时计算
- 与 CLI `bilianalysis serve` 整合为统一入口

---

## 2. 文件结构

```
app/api/
├── __init__.py          # 从 app.py 导入 create_app 并导出
├── app.py               # create_app(config) -> FastAPI + 异常处理 + CORS
├── deps.py              # Depends: get_config, get_runner, get_engine
├── schemas.py           # API 请求/响应模型
├── errors.py            # AppError 业务异常
└── router/
    ├── __init__.py
    ├── crawler.py        # /api/crawler
    ├── analysis.py       # /api/analysis + /stats /clusters /predictions
    ├── tasks.py          # /api/tasks + /{name}/run + /{name}/history
    └── config.py         # /api/config
```

**原则：** API 层只做参数解析 + 响应拼接。业务逻辑全在 `src/bilianalysis/` 已有模块中。`schemas.py` 只定义 API 独有的包装模型，引擎已有的 `CleanReport`/`StatReport` 等直接复用。

---

## 3. App 工厂

### `app.py`

```python
from collections import deque
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bilianalysis.config.model import AppConfig
from bilianalysis.scheduler.models import RunRecord
from app.api.router import crawler, analysis, tasks, config


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(title="BiliAnalysis API", version="0.1.0")

    # 运行时共享状态
    app.state.config = config
    app.state.run_history: deque[RunRecord] = deque(maxlen=200)

    # CORS（前端开发）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(crawler.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(config.router, prefix="/api")

    # 全局异常处理
    _register_error_handlers(app)

    return app
```

### `__init__.py`

```python
from app.api.app import create_app

__all__ = ["create_app"]
```

---

## 4. 依赖注入 (`deps.py`)

```python
from typing import Annotated
from fastapi import Request, Depends

from bilianalysis.config.model import AppConfig
from bilianalysis.engine.base import AnalysisEngine
from bilianalysis.scheduler.runner import PipelineRunner


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_runner(config: Annotated[AppConfig, Depends(get_config)]) -> PipelineRunner:
    return PipelineRunner(config)


def get_engine(config: Annotated[AppConfig, Depends(get_config)]) -> AnalysisEngine:
    from bilianalysis.engine import create_engine
    return create_engine(config)
```

路由函数签名示例：
```python
@router.post("/crawler")
async def trigger_crawl(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
) -> TaskTriggerResponse:
    ...
```

---

## 5. 路由设计

### 5.1 `/api/crawler`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/crawler` | 触发爬取，后台异步执行，返回 202 + run_id |
| `GET` | `/crawler` | 返回 `CrawlerStatus`（读 progress.json） |

**POST 流程：**
1. 创建 `RunRecord(pipeline="crawler", trigger="manual")`
2. `asyncio.create_task` 跑 `CrawlRunner`
3. 任务完成后更新 `run_history` 中对应记录
4. 返回 202 + run_id

### 5.2 `/api/analysis`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/analysis` | 触发完整分析（clean→stats→cluster→predict），202 |
| `GET` | `/analysis` | 返回 `AnalysisOverview` |
| `GET` | `/analysis/stats` | 返回 `StatReport` |
| `GET` | `/analysis/clusters` | 返回 `ClusterReport` |
| `GET` | `/analysis/predictions` | 返回 `PredictionReport` |

**GET 数据来源策略：**
1. 先读 `reports/{stats,clusters,predictions}.json`
2. 文件不存在 → 现场调用 `engine.statistics()` 等，结果缓存到 `reports/` 并返回
3. 引擎不存在（未安装 pyspark 且选了 spark）→ 返回 503

### 5.3 `/api/tasks`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/tasks` | 列出所有流水线配置 |
| `POST` | `/tasks/{name}/run` | 触发指定流水线，202 |
| `GET` | `/tasks/{name}/history` | 执行历史（最近 50 条），支持 `?limit=` |

**`GET /tasks` 返回：**
```json
{
  "pipelines": [
    {"name": "full", "schedule": "0 12 * * 6", "steps": ["crawl","clean_data","statistics","clustering","prediction"], "step_failure": "stop"},
    {"name": "quick", "schedule": "0 8 * * *", "steps": ["crawl","statistics"], "step_failure": "skip"}
  ]
}
```

### 5.4 `/api/config`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/config` | 返回当前完整生效配置 |
| `PUT` | `/config` | 更新运行时配置，可选持久化 |

**PUT 请求体：**
```json
{
  "section": "crawler",
  "values": {"mode": "concurrent", "concurrency": 8},
  "persist": true
}
```

`persist=true` 时写回 `config.yaml`。`section` 支持 `crawler` | `analysis` | `data` | `scheduler`。

---

## 6. Schemas (`schemas.py`)

只定义 API 独有的包装模型。引擎报告直接复用 `bilianalysis.engine.base`。

```python
# ── 通用 ──
class TaskTriggerResponse(BaseModel):
    run_id: str
    pipeline: str
    status: str          # "accepted"

# ── 爬虫 ──
class CrawlerStatus(BaseModel):
    total_weeks: int
    crawled: int
    failed: dict[int, str]
    last_run: datetime | None
    is_running: bool

# ── 分析 ──
class AnalysisOverview(BaseModel):
    last_clean: CleanReport | None       # from engine.base
    last_stats: StatReport | None
    last_cluster: ClusterReport | None
    last_prediction: PredictionReport | None

# ── 任务 ──
class PipelineInfo(BaseModel):
    name: str; schedule: str; steps: list[str]; step_failure: str

class PipelineListResponse(BaseModel):
    pipelines: list[PipelineInfo]

class RunHistoryItem(BaseModel):
    run_id: str; pipeline: str; trigger: str
    started_at: datetime; finished_at: datetime | None
    status: str; step_count: int; failed_step: str | None

# ── 配置 ──
class ConfigUpdateRequest(BaseModel):
    section: Literal["crawler", "analysis", "data", "scheduler"]
    values: dict
    persist: bool = False
```

---

## 7. 错误处理

### 业务异常 (`errors.py`)

```python
class AppError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail

class TaskNotFound(AppError):
    def __init__(self, name):
        super().__init__(404, f"Task '{name}' not found")

class PipelineNotFound(AppError):
    def __init__(self, name):
        super().__init__(404, f"Pipeline '{name}' not found")

class ConfigInvalid(AppError):
    def __init__(self, msg):
        super().__init__(400, f"Invalid config: {msg}")

class EngineUnavailable(AppError):
    def __init__(self):
        super().__init__(503, "Analysis engine not available")
```

### 全局 handler（`app.py` 内）

```python
def _register_error_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_handler(request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

---

## 8. ECharts 适配

现有引擎报告模型与 ECharts 数据格式直接匹配：

| 模型 | 字段形状 | ECharts 图表 |
|------|----------|-------------|
| `CategoryStats[]` | `{tname, video_count, avg_view, avg_like}` | 柱状图 / 饼图 |
| `CreatorStats[]` | `{name, appearance_count, total_view}` | 横向柱状图 |
| `WeeklyTrend[]` | `{week_number, avg_view, avg_like}` | 折线趋势图 |
| `ClusterResult.scatter_data` | `{labels, x, y}` | 散点图 |
| `PredictionResult.fitted/forecast` | `{week_number, actual, predicted}` | 双线对比图 |

**已知缺口：** `SparkEngine.clustering()` 的 `scatter_data` 当前为空 `{labels:[], x:[], y:[]}`（Spark 无 PCA），前端需做降级处理。

---

## 9. 启动方式

### CLI 子命令

在 `app/cli/` 新增 `serve_cmd.py`，注册为 `bilianalysis serve`：

```python
# app/cli/__init__.py 追加
from app.cli.serve_cmd import serve_app
app.add_typer(serve_app, name="serve", help="Start API server")
```

```
uv run bilianalysis serve --port 8080 --config config.yaml
```

### 快捷入口

```toml
[project.scripts]
bilianalysis = "app.cli:app"
bilianalysis-serve = "app.cli.serve_cmd:main"
```

### 启动流程

1. `load_config(config_path)` → AppConfig
2. `create_app(config)` → FastAPI
3. `uvicorn.run(app, host="127.0.0.1", port=port)`

---

## 10. 依赖

新增依赖：

```toml
dependencies = [
    # ... 已有
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
]
```

---

## 11. 测试策略

| 类别 | 数量 | 内容 |
|------|------|------|
| 路由集成测试 | 8 | 每个 GET/POST 端点，用 `TestClient` |
| 异常处理 | 2 | 404/500 响应格式 |
| 配置 PUT | 2 | persist=true/false |
| deps 注入 | 1 | 依赖链完整性 |
| 总计 | ~13 | 全 mock，不依赖真实网络/Spark |

---

## 12. 已知缺口 & 未来扩展

- `SparkEngine.scatter_data` 为空，后续可加 Spark ML PCA
- OpenAPI 自动文档由 FastAPI 生成，无需额外维护
- Cookie 管理通过 `PUT /api/config` + `scheduler` 流水线配置注入
- SSE 实时推送待后续升级
