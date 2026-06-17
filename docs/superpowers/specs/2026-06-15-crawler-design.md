# 数据采集模块设计

Date: 2026-06-15 | Status: approved

## 概述

Bilibili "每周必看"数据采集模块。爬取 348+ 期、约 12,700+ 条视频的完整历史数据。

## API 端点

两个社区发现的非官方端点，无需认证：

| 端点 | 说明 |
|------|------|
| `GET /x/web-interface/popular/series/list` | 获取所有期数列表 |
| `GET /x/web-interface/popular/series/one?number={n}` | 获取指定期数视频详情 |

- 响应结构：`config`（期次元信息）+ `list`（视频数组，含 owner + stat）
- 每期约 30 个视频

## 模块设计

### 文件结构

```
src/
├── utils/
│   ├── fetch.py          ← 重写
│   └── ua.py            ← 不变
└── crawler/
    ├── api.py            ← 新建
    ├── storage.py        ← 新建
    └── pipeline.py       ← 新建
data/raw/
├── week_001.json
├── week_002.json
└── progress.json
main.py                   ← 不动
```

### fetch.py — 异步 HTTP 工具

不定义 HttpClient 类。Session 由调用方创建和注入，符合 aiohttp 原生的异步模式。

**常量**：
- `ua` — 共享 UserAgent 实例（从 `ua.py` 导入）
- `DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=3)`

**异常**：
- `HttpError` — 请求失败时抛出（非 200、网络错误等），附带 status 和 message

**函数**：

```python
def create_session(timeout: ClientTimeout | None = None) -> aiohttp.ClientSession:
    """创建预配置 Session：自动注入随机 UA header + 超时"""

async def get(session: aiohttp.ClientSession, url: str,
              headers: dict | None = None) -> dict | list | str:
    """GET 请求。JSON 响应返回解析后的 dict/list；否则返回文本。失败抛 HttpError"""

async def post(session: aiohttp.ClientSession, url: str,
               data: dict | None = None, json: dict | None = None,
               headers: dict | None = None) -> dict | list | str:
    """POST 请求，同上"""
```

**设计要点**：
- `ua.random` 在每次 `create_session` 时注入一次（session 内所有请求共用同一个 UA）
- 若调用方需要每次请求换 UA，可在 headers 参数覆盖
- Session 关闭由调用方负责（`await session.close()`）
- `ua.py` 保持不变

### api.py — Bilibili API 封装

封装两个 Bilibili API 端点，直接使用 fetch.py 的函数。

```python
BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"

async def list_series(session: aiohttp.ClientSession) -> list[dict]:
    """获取所有期数列表。返回 data.list，按 number 升序排列"""

async def get_weekly_videos(session: aiohttp.ClientSession,
                            number: int) -> dict:
    """获取指定期数的完整数据。返回 API 原始 data 字典 {config, list}。
       失败时 HttpError 直接透传，由 pipeline 层捕获处理重试"""
```

**职责边界**：只负责 API 调用和 JSON 解析，不处理重试、不写文件、不控制速率。

### storage.py — 数据存取 + 进度管理

**数据文件**：
- `data/raw/week_{number:03d}.json` — 单期完整数据
  ```json
  {
    "number": 1,
    "config": { /* API 原始 config */ },
    "videos": [ /* API 原始 list，不变形 */ ]
  }
  ```
- `data/raw/progress.json` — 爬取进度
  ```json
  {
    "total_weeks": 348,
    "latest_number": 348,
    "crawled": [1, 2, 3],
    "failed": { "15": "timeout: connect=3s", "200": "status=502" },
    "last_run": "2026-06-15T10:30:00"
  }
  ```

**函数**：

```python
async def save_week(number: int, data: dict) -> None:
    """保存单期 JSON 文件"""

def load_progress() -> dict:
    """读取 progress.json，文件不存在时返回默认空结构"""

def save_progress(state: dict) -> None:
    """写入 progress.json"""

def get_pending_weeks(latest_number: int) -> tuple[list[int], list[int]]:
    """对比 progress.json，返回 (retry, pending)。
       pending: 从未爬取的新期号列表
       retry: 历史失败的期号列表，每次 run 时重新尝试一次"""
```

**设计要点**：
- `save_week` 是异步（文件 IO 用 `aiofiles` 或 `asyncio.to_thread`）
- progress 操作用同步即可（小文件，读写极快）
- `get_pending_weeks` 返回两个列表：`pending`（未爬的新期号）和 `retry`（历史失败的期号，每次 run 时重新尝试一次）
- 目录 `data/raw/` 在首次 save 时自动创建

### pipeline.py — 爬取编排

核心编排层。协调 api + storage，实现重试、续爬、速率控制。

**数据模型** (Pydantic)：

```python
from pydantic import BaseModel
from typing import Literal

class CrawlConfig(BaseModel):
    mode: Literal["sequential", "concurrent"] = "sequential"
    concurrency: int = 3              # 并发数（concurrent 模式）
    request_delay: float = 2.5        # 请求间隔秒（sequential 模式）
    max_retries: int = 3              # 单期重试次数
    retry_delay: float = 1.0          # 重试间隔秒

class CrawlReport(BaseModel):
    total: int                        # API 总期数
    crawled: int                      # 本次新爬取成功数
    skipped: int                      # 已存在跳过的
    failed: int                       # 本次失败数
    failed_weeks: dict[int, str]      # {number: reason}
    duration_seconds: float
```

**函数**：

```python
async def run(config: CrawlConfig = CrawlConfig()) -> CrawlReport:
    """执行一次完整爬取。供外部模块调用。
       流程：
       1. list_series() → 获取所有期号
       2. get_pending_weeks() → 筛选待爬期号
       3. 按 mode 执行爬取循环
       4. 保存进度 + 返回报告
    """
```

**执行流程**：

```
1. session = create_session()
2. series = await api.list_series(session)
3. latest = series[-1]["number"]
4. pending, retry = storage.get_pending_weeks(latest)
5. 先处理 retry 列表（历史失败期号，每个仅尝试 1 次）
   - 成功 → storage.save_week() → 从 failed 移除
   - 失败 → 保留在 failed，更新原因
6. 再处理 pending 列表（新期号，根据 mode）:
   - sequential: for n in pending: await crawl_one(n); sleep(delay)
   - concurrent: asyncio.Semaphore(concurrency); gather tasks
   - 每个 crawl_one(n): 重试 max_retries 次
7. storage.save_progress()
8. await session.close()
9. 返回 CrawlReport
```

**速率控制**：
- sequential：`await asyncio.sleep(request_delay)` 每次请求后
- concurrent：`asyncio.Semaphore(concurrency)` 限制同时请求数，无额外延迟

## 依赖

- `aiohttp` — 已有
- `fake-useragent` — 已有
- `pydantic` — 新增：`uv add pydantic`

## 不在范围内

- 不修改 `main.py`
- 不实现定时调度（Cron/Scheduler）—— 后续用外部定时任务触达 `run()`
- 不做数据清洗/变形 —— 原始 API 数据完整保留
- 不做 Spark/Pandas 分析引擎
