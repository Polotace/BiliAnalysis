# 开发文档

## 一、项目结构

```
BiliAnalysis/
├── src/bilianalysis/
│   ├── utils/
│   │   ├── fetch.py          # 异步 HTTP 客户端（aiohttp 函数式封装）
│   │   └── ua.py             # 共享的 fake_useragent 实例
│   └── crawler/
│       ├── api.py            # Bilibili "每周必看" API 封装
│       ├── storage.py        # 数据持久化 + 进度管理
│       └── pipeline.py       # 爬取编排（限速/重试/续爬/并发）
├── data/raw/                 # 运行时数据（由 storage.py 自动创建）
├── tests/                    # pytest 测试套件
├── docs/
│   ├── README.md             # 项目总体方案
│   ├── dev/                  # 开发文档
│   └── test/                 # 测试文档
└── pyproject.toml            # uv 项目配置
```

## 二、模块设计

### 2.1 fetch.py — HTTP 传输层

**设计原则**：函数式、无状态、Session 由调用方显式注入。

```
调用方创建 Session → 传入 get/post → 返回 Any（JSON 或文本）
                          ↓ 失败抛 HttpError
```

```python
session = create_session()              # 自动注入随机 UA + 超时
data = await get(session, url)          # GET → JSON 或文本
data = await post(session, url, json={}) # POST → JSON 或文本
await session.close()                   # 调用方负责关闭
```

**为什么不用 `HttpClient` 类？**Session 由调用方创建，多个协程可以共享一个 Session 的连接池。类和单例模式反而会增加生命周期管理的复杂度。

**HttpError**：非 200 响应和网络异常统一包装，`status=0` 表示网络层错误，下游通过 `status` 区分重试策略。

**`_jitter` 函数**：`base ± 1s` 随机抖动，串行模式的请求间隔和重试等待都经过随机化，避免触发反爬机制。

### 2.2 api.py — API 封装层

两个 Bilibili API 端点，无需认证：

| 函数 | URL | 返回 |
|------|-----|------|
| `list_series(session)` | `/popular/series/list` | `list[dict]` 所有期数 |
| `get_weekly_videos(session, number)` | `/popular/series/one?number={n}` | `dict` 单期 config + videos |

**异常透传**：api.py 不捕获 `HttpError`，全部抛给 pipeline 层的重试逻辑处理。

### 2.3 storage.py — 持久化层

**数据文件**：

```
data/raw/
├── week_001.json        # {"number": 1, "config": {...}, "videos": [...]}
├── week_002.json
└── progress.json        # ProgressFile 模型的 JSON 序列化
```

**ProgressFile** (Pydantic BaseModel)：

| 字段 | 类型 | 说明 |
|------|------|------|
| `crawled` | `list[int]` | 已成功爬取的期号 |
| `failed` | `dict[int, str]` | 失败期号 → 错误原因 |
| `last_run` | `datetime \| None` | 上次运行时间 |

**并发安全**：`_progress_lock = asyncio.Lock()` 保护 `load_progress` / `save_progress` 的读写竞态。

**关键函数**：

```python
await save_week(number, data)          # 保存单期
progress = await load_progress()       # 读取进度
await save_progress(progress)          # 写入进度
retry, pending = await get_pending_weeks(latest)  # 计算待爬列表
```

`get_pending_weeks` 返回两个列表：
- `retry`：历史失败的期号（每次 `run()` 重试一次）
- `pending`：从未爬取的新期号

### 2.4 pipeline.py — 编排层

**数据模型**：

```python
class CrawlConfig(BaseModel):
    mode: Literal["sequential", "concurrent"] = "sequential"  # 爬取模式
    concurrency: int = 3            # 并发数（仅 concurrent 模式）
    request_delay: float = 2.5      # 请求间隔秒（仅 sequential 模式）
    max_retries: int = 3            # 单期最大重试次数（仅新期号）
    retry_delay: float = 1.0        # 重试间隔秒

class CrawlReport(BaseModel):
    total: int                      # 总期数
    crawled: int                    # 本次成功
    skipped: int                    # 已存在跳过
    failed: int                     # 本次失败
    failed_weeks: dict[int, str]    # 失败详情
    duration_seconds: float         # 耗时
```

**执行流程**：

```
run(config)
 │
 ├── create_session()
 ├── list_series(session)                  → 获取所有期号列表
 ├── get_pending_weeks(latest)            → (retry_list, pending_list)
 ├── [retry phase] 每个失败期号尝试 1 次
 │    ├── 成功 → save_week() → 从 failed 移除
 │    └── 失败 → 保留在 failed
 ├── [pending phase] 按 mode 处理新期号
 │    ├── sequential: for each → _crawl_one() → sleep(_jitter(delay))
 │    └── concurrent: semaphore + gather → _crawl_one()
 ├── save_progress()                       → 写 last_run
 └── return CrawlReport
```

**_crawl_one 重试逻辑**：

```
for attempt in 1..max_retries:
    try get_weekly_videos(number)
    ├── 成功 → save_week → 更新进度 → return True
    └── HttpError → sleep(_jitter(retry_delay)) → continue
全部失败 → 记录到 progress.failed → return False
```

## 三、配置说明

所有配置通过 `CrawlConfig` 传入，无配置文件依赖：

```python
from bilianalysis.crawler import CrawlRunner, CrawlConfig

# 默认保守模式
await CrawlRunner()

# 并发模式
config = CrawlConfig(mode="concurrent", concurrency=5)
await CrawlRunner(config)
```

## 四、扩展指南

### 添加新的分析模块

1. 在 `src/bilianalysis/` 下新建子包（如 `analytics/`）
2. 定义抽象接口（遵循 `docs/README.md` 中的 `AnalysisEngine` 设计）
3. 实现 `PandasEngine` 和 `SparkEngine`

### 添加前端

1. 在 `app/` 下创建 Vue3 + TypeScript 项目
2. 后端 API 在 `app/backend/` 使用 FastAPI

## 五、Git 工作流

- 主分支：`main`
- 开发分支：`feature/<name>`
- 提交前运行 `uv run pytest tests/ -v` 确保 36 测试全绿
