# BiliInsight 项目总体架构设计方案

> 基于 GPT-5.5 初始方案重构，以当前代码库实际状态为准。
> 撰写日期：2026-06-19

---

## 一、当前状态审计

在开始设计之前，先明确哪些已经完成、哪些只是规划。

### 1.1 已建成（不可推翻）

| 模块 | 位置 | 状态 | 说明 |
|------|------|------|------|
| 爬虫 | `src/bilianalysis/crawler/` | **完成** | aiohttp 异步爬虫，含 WBI 签名、Session 轮换、指数退避重试、进度持久化 |
| 分析引擎 ABC | `src/bilianalysis/engine/base.py` | **完成** | 4 步抽象：`clean_data` → `statistics` → `clustering` → `prediction`，含全部报告 Pydantic 模型 |
| Pandas 引擎 | `src/bilianalysis/engine/pandas_engine.py` | **完成** | 543 行，全量加载 raw JSON → 5 张 Parquet → join/groupby/KMeans/PCA/LinearRegression |
| Spark 引擎 | `src/bilianalysis/engine/spark_engine.py` | **完成** | 590 行，PySpark 实现相同接口，支持 HDFS 读写 |
| 调度框架 | `src/bilianalysis/scheduler/` | **完成** | PipelineRunner + TaskContext + CronService + 注册表 + 5 个内建 Task |
| 配置系统 | `src/bilianalysis/config/` | **完成** | AppConfig Pydantic 模型 + YAML loader + config.yaml |
| 数据模型 | `src/bilianalysis/models.py` | **完成** | Weekly / Video / Creator / Category / VideoStat |
| HTTP 工具 | `src/bilianalysis/utils/` | **完成** | aiohttp 封装 + 随机 UA |
| 测试套件 | `tests/` | **完成** | 109 个 pytest-asyncio 测试 |
| 设计原型 | `design-demos/` | **已有** | homepage-v1.html（BiliInsight 品牌、Spotify 风格、蓝色调） |
| FastAPI 后端 | `app/api/` | **部分完成** | app 工厂 + CORS + 错误处理 + 4 组 router（crawler / analysis / tasks / config） |
| Vue3 前端 | `app/ui/` | **部分完成** | 4 页面（首页/统计/聚类/预测）+ ~15 组件 + Vitest + Playwright e2e |

### 1.2 关键实现细节（GPT 方案未覆盖）

- **爬虫用 aiohttp，不用 Requests**。Session 由调用方注入，支持连接池复用。
- **引擎工厂**在 `engine/__init__.py` 的 `create_engine(config)` —— 一行切换 Pandas/Spark。
- **数据流已经是**：raw JSON → `_extract_tables()` → 5 张 DataFrame → fill/dedup/convert/outlier → Parquet。
- **引擎 4 步全部实现**，不是接口空壳。`statistics()` 做 join+周匹配+groupby，`clustering()` 做 StandardScaler+KMeans+PCA+silhouette，`prediction()` 做周聚合+LinearRegression+未来 4 周预测。
- **调度器已工作**：`PipelineRunner.run("crawl")` 走完整流水线，惰性创建引擎，finally 清理 Spark。
- **配置文件已存在**：`config.yaml` 含 crawler/analysis/data/scheduler 四个节。
- **FastAPI 已有骨架**：`app/api/app.py` 工厂函数 + CORS + 4 组 router，依赖注入 config/runner/engine。
- **前端已有 4 页**：首页（KPI 卡片 + 分区柱状图 + UP 主列表 + 趋势迷你图）、统计页、聚类页、预测页。使用 Vue3 + Element Plus + ECharts + Alova，含 Vitest + Playwright 测试。

### 1.3 尚未建设

- PostgreSQL 存储层（课程数据库设计）
- raw JSON → PostgreSQL 的数据加载（`app/api/db/loader.py`）
- `src/bilianalysis/etl/` 数据转换包（raw JSON → typed records）
- `src/bilianalysis/warehouse/` 数据仓库分层（DWD/DWS/ADS）
- 内容特征分析（TF-IDF / TextRank / WordCloud）
- 视频/UP主/分区详情 API 端点（当前仅有 crawler + analysis + tasks + config）
- 前端视频库/视频详情/UP主榜/UP主详情/趋势页（当前有首页/统计/聚类/预测 4 页）

---

## 二、产品定位与品牌

| 维度 | GPT 方案 | 当前实际 | 采纳 |
|------|----------|----------|------|
| 产品名 | BiliInsight | BiliAnalysis（包名） | **BiliInsight** 作为产品名；Python 包名保持 `bilianalysis` |
| 定位 | 内容发现 + 数据运营 + 数据分析 | 数据分析平台 | 采纳 GPT 方案 |
| 风格 | 40% Spotify + 30% Steam + 20% Notion + 10% Apple | 设计原型已体现 | 采纳，原型已对齐 |

### 品牌决策

- **产品名 BiliInsight**：前端标题、README、文档使用
- **包名保持 `bilianalysis`**：Python 包名不更改。改名涉及全部 import、测试 mock 路径、pyproject.toml 的破坏性重构，无实际收益

---

## 三、总体架构

### 3.1 双轨数据流

GPT 方案提出了一条线性流水线：Bilibili API → 数据采集 → PostgreSQL → Spark ETL → Parquet → 分析 → FastAPI → Vue3。但当前代码库的采集和分析是解耦的，且分析引擎已直接消费 raw JSON。强行在中间插入 PostgreSQL 会破坏已有实现。

**新架构采用双轨设计**：

```
                    ┌──────────────────────────────────────┐
                    │         Bilibili API                 │
                    └──────────┬───────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Crawler (aiohttp)  │  ← 已有，不动
                    │   pipeline.py        │
                    └──────────┬───────────┘
                               │
                         data/raw/*.json
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
    ┌──────────────────────┐      ┌──────────────────────┐
    │  轨道 A：业务轨        │      │  轨道 B：分析轨        │
    │                      │      │                      │
    │  bilianalysis 库模块  │      │ Engine (Pandas/Spark)│
    │  提供数据转换函数       │      │ (课程 Spark 分析)     │
    │  (不接触数据库)        │      └──────────┬───────────┘
    └──────────┬───────────┘                 │
               │                    data/processed/*.parquet
               │                    data/reports/*.json
               │                             │
               ▼                             │
    ┌──────────────────────┐                 │
    │   app/api/           │◄────────────────┘
    │   FastAPI 应用        │
    │   (唯一接触 PG 的模块)  │
    │                      │
    │   PostgreSQL         │
    │   (课程数据库设计)     │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │   app/ui/            │
    │   Vue3 + ECharts     │
    │   TailwindCSS        │
    └──────────────────────┘
```

**为什么是双轨而非串行**：

1. **爬虫和分析已解耦**。爬虫写完 raw JSON 就退出了。引擎独立读取 raw JSON。
2. **PostgreSQL 是增量需求**。当前系统完全不需要它。把它放在爬虫和引擎之间会破坏已有数据流。
3. **双轨满足双重课程要求**：
   - 轨道 A（PostgreSQL）→ 数据库课程：ER 建模、范式化、SQL 查询
   - 轨道 B（Parquet + Spark）→ 大数据课程：ETL、Spark SQL、MLlib、分布式计算
4. **两轨在 FastAPI 层汇聚**。API 同时查询 PostgreSQL（视频详情、UP 主信息）和读取分析报告（统计、聚类、预测），前端无感知。

### 3.2 关于 Parquet 与 PostgreSQL "重复存储" 的解释

引擎的 `_extract_tables()` 将 raw JSON 拆为 5 张 Parquet 表，PostgreSQL 也有对应的 6 张业务表。这并非无意义的冗余，而是**用途决定形态**：

| 维度 | Parquet（轨道 B） | PostgreSQL（轨道 A） |
|------|-------------------|---------------------|
| 用途 | 分析计算（groupby/join/KMeans/回归） | 业务查询（分页列表/详情/搜索/关联） |
| 存储模型 | 列式，高压缩率 | 行式，B-tree 索引 |
| 查询模式 | 全列扫描、聚合 | 点查、范围查、JOIN |
| 消费方 | Pandas / PySpark / Scikit-Learn | FastAPI → Vue3 |
| 数据来源 | raw JSON（引擎直接读取） | raw JSON（FastAPI 加载入库） |

两条轨道**都从 raw JSON 出发**，各自产出适合自己消费方的数据格式。Parquet 不适合逐行点查（API 查一个视频详情要走全表扫描），PostgreSQL 不适合列聚合（groupby 数百周数据不如 Spark DataFrame 快）。

### 3.3 库模块与应用的职责边界

这是本次架构最关键的约束：

```
┌─────────────────────────────────────────────────────────┐
│  src/bilianalysis/  纯 Python 库                        │
│                                                         │
│  允许：计算、转换、文件 I/O、HTTP 请求、Parquet 读写     │
│  禁止：导入 sqlalchemy / asyncpg / 任何数据库驱动         │
│  禁止：建立数据库连接、执行 SQL、管理连接池                │
└─────────────────────────────────────────────────────────┘
                              │
                              │ import (单向依赖)
                              ▼
┌─────────────────────────────────────────────────────────┐
│  app/api/  FastAPI 应用                                  │
│                                                         │
│  允许：导入 bilianalysis、管理 PG 连接池、执行 SQL        │
│  负责：PostgreSQL 一切操作、API 端点、请求/响应模型        │
└─────────────────────────────────────────────────────────┘
```

库模块不接触数据库。它提供纯函数——接收数据，返回数据。FastAPI 是唯一连接 PostgreSQL 的模块。

### 3.4 与 GPT 方案的关键差异

| 决策点 | GPT 方案 | 新方案 | 理由 |
|--------|----------|--------|------|
| 采集层技术 | FastAPI + Requests | aiohttp crawler（已有） | 爬虫已成熟，重写无意义 |
| 数据流顺序 | PG → Spark → Parquet | raw JSON → PG（轨道 A）∥ raw JSON → Parquet → 分析（轨道 B） | 保护已有引擎，双轨独立 |
| 库模块接触 DB | 隐含允许 | 明确禁止 | 职责分离，FastAPI 唯一持有 DB 连接 |
| 项目结构 | 顶层 biliinsight/ 多子包 | `app/api/` + `app/ui/` + `src/bilianalysis/` | 应用与库分离 |
| Python 版本 | 3.12+ | 3.13+（已有） | 已锁定 |
| 前端 CSS | TailwindCSS | TailwindCSS | 采纳，设计原型已体现 |

---

## 四、轨道 A：PostgreSQL 业务数据库

### 4.1 定位

PostgreSQL 专用于：
- 实体关系建模（数据库课程要求）
- 规范化业务数据存储
- API 业务查询（视频详情、UP 主搜索、按期浏览）

**不承担分析计算任务**。分析由轨道 B 的引擎完成。

**PostgreSQL 仅由 `app/api/` 驱动**。`src/bilianalysis/` 库模块不导入任何数据库驱动，不持有连接，不执行 SQL。

### 4.2 表设计（6 张表，每个字段含 COMMENT）

```sql
-- ═══ 周刊信息 ═══
CREATE TABLE weekly (
    number     INTEGER PRIMARY KEY,   -- 期号，如 1, 2, 3...
    subject    TEXT,                   -- 当期主题，如"一周热门盘点"
    name       TEXT,                   -- 当期名称，如"每周必看 第1期"
    start_time TIMESTAMPTZ,           -- 当周起始时间
    end_time   TIMESTAMPTZ            -- 当周结束时间
);

-- ═══ UP 主 ═══
CREATE TABLE creator (
    mid  INTEGER PRIMARY KEY,         -- B站 UP 主唯一 ID
    name TEXT,                         -- UP 主昵称
    face TEXT                          -- 头像图片 URL
);

-- ═══ 分类（三级） ═══
CREATE TABLE category (
    tid       INTEGER PRIMARY KEY,    -- 三级分类 ID（B站 tid）
    tname     TEXT,                    -- 三级分类名，如"单机游戏"
    tid_v2    INTEGER,                -- 二级分类 ID（从 rcmd_reason 提取，可能为空）
    tname_v2  TEXT                     -- 二级分类名，如"游戏"
);

-- ═══ 视频 ═══
CREATE TABLE video (
    aid          INTEGER PRIMARY KEY, -- B站视频 AV 号
    bvid         TEXT,                -- B站视频 BV 号
    title        TEXT,                -- 视频标题
    description  TEXT,                -- 视频简介/描述
    duration     INTEGER,            -- 视频时长（秒）
    pubdate      TIMESTAMPTZ,        -- 发布时间
    cid          INTEGER,            -- B站 CID（评论/弹幕分区标识）
    video_url    TEXT,
    cover_url    TEXT,               -- 封面图片 URL
    creator_mid  INTEGER REFERENCES creator(mid),   -- 所属 UP 主
    category_tid INTEGER REFERENCES category(tid)    -- 所属三级分类
);

-- ═══ 视频统计（1:1 关联 video） ═══
CREATE TABLE video_stat (
    aid      INTEGER PRIMARY KEY REFERENCES video(aid), -- 视频 AV 号
    view     BIGINT,                   -- 播放量
    like_cnt BIGINT,                   -- 点赞数
    coin     BIGINT,                   -- 投币数
    favorite BIGINT,                   -- 收藏数
    share    BIGINT,                   -- 分享数
    reply    BIGINT,                   -- 评论数
    danmaku  BIGINT                    -- 弹幕数
);

-- ═══ 周刊-视频关联（N:M） ═══
CREATE TABLE weekly_video (
    weekly_number INTEGER REFERENCES weekly(number), -- 所在周次
    aid           INTEGER REFERENCES video(aid),     -- 上榜视频
    PRIMARY KEY (weekly_number, aid)                 -- 同一视频可在不同周次上榜
);
```

**与已有模型的对齐**：

| PG 表 | 已有 Pydantic 模型 | 已有 Parquet 表 |
|-------|-------------------|-----------------|
| `weekly` | `Weekly` | `Weekly.parquet` |
| `creator` | `Creator` | `Creator.parquet` |
| `category` | `Category` | `Category.parquet` |
| `video` | `Video` | `Video.parquet` |
| `video_stat` | `VideoStat` | `VideoStat.parquet` |
| `weekly_video` | 无（新增） | 无（引擎通过 pubdate 范围匹配推导） |

### 4.3 数据流入 PostgreSQL 的方式

**库模块**（`src/bilianalysis/`）提供纯转换函数，不接触数据库：

```python
# src/bilianalysis/etl/transform.py（示例）
def transform_week(raw_json: dict) -> dict:
    """将单个 week_NNN.json 转换为 6 组 record dict。
    纯函数，无 I/O 副作用，不导入数据库驱动。"""
    ...
    return {
        "weekly": {...},
        "creators": [...],
        "categories": [...],
        "videos": [...],
        "video_stats": [...],
        "weekly_videos": [...],
    }
```

**FastAPI 应用**（`app/api/`）负责数据库写入：

```python
# app/api/db/loader.py（示例）
async def load_week(pg_session: AsyncSession, records: dict) -> None:
    """将库模块产出的 records 写入 PostgreSQL。
    只有这里的代码可以导入 sqlalchemy / asyncpg。"""
    await pg_session.execute(insert(Weekly).values(**records["weekly"]).on_conflict_do_nothing())
    await pg_session.execute(insert(Creator).values(records["creators"]).on_conflict_do_nothing())
    ...
```

**数据流**：

```
data/raw/week_NNN.json
        │
        ▼
src/bilianalysis/etl/transform.py    ← 库模块：纯转换，不接触 DB
        │
        ▼
    6 组 records (dict)
        │
        ▼
app/api/db/loader.py                  ← FastAPI：唯一执行 SQL 的地方
        │
        ▼
    PostgreSQL
```

### 4.4 数据库配置位置

数据库配置**属于 FastAPI 应用**，不在全局 `config.yaml` 中。

方式：FastAPI 应用在 `app/api/` 内自行管理配置，可以是 `.env` 文件或应用级 `config.py`：

```python
# app/api/config.py
from pydantic_settings import BaseSettings

class ApiSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/biliinsight"
    database_pool_size: int = 5

    model_config = {"env_file": ".env"}
```

全局 `config.yaml` 不新增 `database` 节。数据库配置完全是 FastAPI 应用自己的事。

---

## 五、轨道 B：分析引擎与数据仓库

### 5.1 现状

引擎已经完整实现，无需改动核心逻辑：

```
raw JSON → clean_data() → 5 张 Parquet（Weekly/Video/Creator/Category/VideoStat）
                        → statistics() → StatReport (overall + by_category + by_creator + by_week)
                        → clustering() → ClusterReport (KMeans k=3 + PCA 散点数据)
                        → prediction() → PredictionReport (LinearRegression + 4 周预测)
```

报告写入 `data/reports/`（JSON 格式）。

### 5.2 与 PostgreSQL 的关系

`_extract_tables()` 将数据拆为 5 张 Parquet 表，PostgreSQL 也有结构相似的 6 张表。这不是重复，详见 [3.2 节](#32-关于-parquet-与-postgresql-重复存储的解释)。简言之：Parquet 服务分析引擎（列式聚合），PostgreSQL 服务 API（行式点查）。两套数据都来自 raw JSON，各自独立加载，互不依赖。

### 5.3 DWD/DWS/ADS 数据仓库分层（增强）

当前 Parquet 产出停在 ODS 层（5 张独立表）。GPT 方案提出了 DWD/DWS/ADS 三层建模。这些分层构建在引擎输出之上，是增值层，不是替代引擎。

#### DWD 层：明细宽表

**输入**：`Video.parquet` + `VideoStat.parquet` + `Creator.parquet` + `Category.parquet`

**输出**：`dwd_fact_video.parquet`——一张大宽表，一行一个视频，包含所有维度：

```
weekly_number, aid, bvid, title,
up_mid, up_name,
category_lv1, category_lv2, category_lv3,
view, like, coin, favorite, share, reply, danmaku,
like_rate, coin_rate, favorite_rate, share_rate, reply_rate, danmaku_rate,
duration, pubdate
```

**实现位置**：`src/bilianalysis/warehouse/dwd.py`（纯计算，不接触数据库）

#### DWS 层：汇总表

| 表 | 粒度 | 来源 |
|----|------|------|
| `dws_up_statistics.parquet` | up_mid | DWD groupby up_mid |
| `dws_category_statistics.parquet` | category | DWD groupby category_lv2 |
| `dws_weekly_statistics.parquet` | weekly_number | DWD groupby weekly_number |

**实现位置**：`src/bilianalysis/warehouse/dws.py`

DWS 是持久化的汇总数据表（可被后续查询复用），与 `statistics()` 的一次性 JSON 报告不同——报告是每次调用即时计算，DWS 是物化存储。

#### ADS 层：面向前端

| 表 | 内容 | 来源 |
|----|------|------|
| `ads_top_up.parquet` | 热门 UP 主 TOP20 | DWS up_statistics 排序 |
| `ads_hot_video.parquet` | 热门视频 TOP50 | DWD 按播放量排序 |
| `ads_category_trend.parquet` | 分区趋势 | DWS category × weekly 交叉汇总 |
| `ads_video_cluster.parquet` | 聚类结果 + 标签 | 引擎 clustering() 输出 + DWD 维度 join |

**实现位置**：`src/bilianalysis/warehouse/ads.py`

### 5.4 内容特征分析（新增）

GPT 方案提出了 TF-IDF / TextRank / WordCloud 文本分析。当前引擎未涉及。作为分析模块的扩展：

- **输入**：`Video.parquet` 的 `title` 字段 + `Weekly.parquet` 的 `subject` 字段
- **方法**：`jieba` 分词 → `TfidfVectorizer` → 关键词提取
- **产出**：`data/reports/keywords.json`（每周热词 + 词云数据）
- **实现位置**：`src/bilianalysis/warehouse/keywords.py`（纯计算）

---

## 六、FastAPI 后端

### 6.1 当前实际结构

`app/api/` 已实现应用骨架和 4 组端点：

```
app/api/
├── __init__.py
├── app.py              # create_app(config) 工厂：CORS + router 注册 + 错误处理
├── deps.py             # get_config / get_runner / get_engine 依赖注入
├── errors.py           # AppError 异常体系（404/400/503）
├── schemas.py          # API 响应模型（复用 bilianalysis.engine.base 报告模型）
└── router/
    ├── __init__.py
    ├── crawler.py      # POST /api/crawler（触发采集） + GET /api/crawler（进度）
    ├── analysis.py     # POST /api/analysis（触发完整分析流水线）
    │                   # GET  /api/analysis（概览：clean/stats/cluster/prediction）
    │                   # GET  /api/analysis/stats
    │                   # GET  /api/analysis/clusters
    │                   # GET  /api/analysis/predictions
    ├── tasks.py        # GET  /api/tasks（列出所有流水线）
    │                   # POST /api/tasks/{name}/run（触发指定流水线）
    │                   # GET  /api/tasks/{name}/history（执行历史）
    └── config.py       # GET/PUT /api/config
```

**关键约束**：`src/bilianalysis/` 库模块绝不导入数据库驱动。

### 6.2 待新增：数据库层

当前 API 不接触 PostgreSQL——分析端点直接读报告文件或调用引擎。这是正确的架构方向。PostgreSQL 集成需要新增：

```
app/api/
├── config.py             # ★ 新增：ApiSettings（含 database_url，仅此应用使用）
├── db/                   # ★ 新增：数据库访问层
│   ├── schema.py         #   SQLAlchemy ORM 模型（6 张表）
│   ├── loader.py         #   数据库写入（唯一执行 SQL INSERT 的地方）
│   └── queries.py        #   查询封装
└── router/
    ├── weeks.py          # ★ 新增：GET /api/weeks, GET /api/weeks/{number}
    ├── videos.py         # ★ 新增：GET /api/videos, GET /api/videos/{aid}
    ├── creators.py       # ★ 新增：GET /api/creators, GET /api/creators/{mid}
    └── categories.py     # ★ 新增：GET /api/categories
```

`app/api/db/` 是项目中唯一可以 `import sqlalchemy` / `import asyncpg` 的目录。

### 6.3 数据源策略

| 端点类型 | 数据源 | 说明 |
|----------|--------|------|
| Crawler 触发/状态 | CrawlRunner + progress.json | 已有 |
| Analysis 触发/结果 | PipelineRunner + 报告文件 | 已有 |
| Pipeline 管理 | config.scheduler.pipelines | 已有 |
| 视频列表/详情 | PostgreSQL（待建） | 需要分页、搜索、关联 |
| UP 主列表/详情 | PostgreSQL（待建） | 关联视频数聚合 |
| 分区列表 | PostgreSQL（待建） | 简单维度查询 |
| 统计/聚类/预测 | `data/reports/*.json` | 已有，引擎产出 |

### 6.4 技术细节

- **FastAPI 工厂模式**：`create_app(config)` 返回配置好的 app，由 uvicorn 启动
- **依赖注入**：`get_config`（读 app.state）、`get_runner`（创建 PipelineRunner）、`get_engine`（惰性创建引擎）
- **后台任务**：`asyncio.create_task()` 跑爬虫/分析，返回 202 + run_id
- **CORS**：开发环境允许所有来源
- **缓存策略**：分析报告端点优先读缓存 JSON，缓存未命中才调用引擎实时计算
- **无 Alembic**：6 张表结构稳定，DDL 在应用启动时直接执行

---

## 七、Vue3 前端

### 7.1 当前实际结构

`app/ui/` 已实现完整的 Vue3 项目，含 4 个页面和 ~15 个组件：

```
app/ui/
├── index.html
├── package.json              # Vue 3.5 + Element Plus 2.9 + ECharts 5 + Alova
├── vite.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── tsconfig.json
├── pnpm-lock.yaml
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── env.d.ts
│   ├── router/index.ts       # 4 条路由：/ /analysis/stats /analysis/clusters /analysis/predictions
│   ├── types/api.ts          # StatReport / ClusterReport / PredictionReport 类型
│   ├── styles/theme.css      # 设计 token + TailwindCSS
│   ├── composables/
│   │   ├── useApi.ts         # Alova 实例 + fetchStats/Clusters/Predictions + useXxx hooks
│   │   └── useChart.ts       # ECharts 实例管理 + 响应式 resize
│   ├── pages/
│   │   ├── HomePage.vue
│   │   └── analysis/
│   │       ├── StatsPage.vue
│   │       ├── ClusterPage.vue
│   │       └── PredictPage.vue
│   └── components/
│       ├── layout/
│       │   ├── PageShell.vue
│       │   └── TopNav.vue
│       ├── home/
│       │   ├── HeroSection.vue
│       │   ├── KpiCardRow.vue
│       │   ├── CategoryBar.vue
│       │   ├── CreatorTopList.vue
│       │   └── TrendMiniChart.vue
│       ├── analysis/
│       │   ├── SubNavTabs.vue
│       │   ├── CategoryPanel.vue
│       │   ├── CreatorTable.vue
│       │   ├── ClusterCards.vue
│       │   ├── FeatureImportance.vue
│       │   └── ForecastCards.vue
│       ├── charts/
│       │   ├── CategoryBarChart.vue
│       │   ├── TrendLineChart.vue
│       │   ├── ClusterScatter.vue
│       │   └── FitLineChart.vue
│       └── shared/
│           ├── SectionHeader.vue
│           └── StatCard.vue
├── e2e/                       # Playwright 视觉回归测试
│   ├── visual.spec.ts
│   └── visual.spec.ts-snapshots/   # 4 张基准截图
├── dist/                      # 已构建产物
└── test-results/              # 最新测试结果
```

### 7.2 技术栈（实际）

| 层 | 选择 | 说明 |
|----|------|------|
| 框架 | Vue 3.5 + Composition API | `<script setup>` |
| 语言 | TypeScript 5.6 | 严格模式 |
| 构建 | Vite 6 | 标准配置 |
| 路由 | Vue Router 4 | 4 条路由 |
| 组件库 | **Element Plus 2.9** | 实际已引入（非原 GPT 方案的纯 Tailwind） |
| 样式 | **TailwindCSS 4** + 自定义 theme.css | 两者并存 |
| 图表 | ECharts 5 | 通过 useChart composable 管理 |
| HTTP | **Alova 3** | 已封装 fetchStats/Clusters/Predictions |
| 测试 | Vitest 2 + Playwright 1.49 | 单元 + e2e 视觉回归 |
| 包管理 | **pnpm** | lockfile 已存在 |

### 7.3 已实现页面

```
/                          首页
                             ├── HeroSection（渐蓝 Banner + 标题"发现每周好内容"）
                             ├── KpiCardRow（4 张统计卡片：总视频/均播放/均点赞/活跃UP主）
                             ├── CategoryBar（热门分区横向柱状图）
                             ├── CreatorTopList（活跃 UP 主 Top 5 排行）
                             └── TrendMiniChart（周均播放趋势 SVG 迷你图）

/analysis/stats            统计分析页
                             ├── 基础统计卡片
                             ├── CategoryPanel（分区统计面板）
                             ├── CreatorTable（UP 主排行表）
                             └── TrendLineChart（周趋势 ECharts 折线图）

/analysis/clusters         聚类分析页
                             ├── ClusterScatter（PCA 散点图）
                             ├── ClusterCards（各类特征卡片）
                             └── FeatureImportance（特征重要性）

/analysis/predictions      预测页
                             ├── FitLineChart（历史拟合 + 预测曲线）
                             └── ForecastCards（未来 4 周预测卡片）
```

### 7.4 待新增页面

```
/videos                    视频库（搜索 + 筛选 + 卡片网格 + 分页）
/videos/:aid               视频详情（信息 + 互动数据 + 上榜记录）

/creators                  UP 主榜（排行榜）
/creators/:mid             UP 主详情（统计 + 上榜视频列表）

/trends                    趋势分析（播放/点赞率/投币率多线图 + 分区堆叠图）
```

### 7.5 设计原则（采纳 GPT 方案 + 设计原型）

- **内容优先**：先看到视频，再看到数据，最后看到图表
- **禁止后台风格**：无左侧导航抽屉、无面包屑、无 CRUD 表格
- **TopNav + 内容区**：sticky 顶栏（毛玻璃效果）+ 全宽内容
- **色彩系统**：
  - 主色 `#00AEEC`（B站蓝）
  - 背景 `#FAFAFA` / 卡片 `#FFFFFF`
  - 文字 `#111827` / `#6B7280`
- **字体**：Inter（英文/数字）+ PingFang SC / HarmonyOS Sans SC（中文）
- **数字**：`font-variant-numeric: tabular-nums` 对齐

### 7.6 与 GPT 方案前端设计的对齐

| GPT 方案要点 | 采纳情况 |
|-------------|----------|
| Spotify 40% — 大图卡片、沉浸浏览 | ✅ 首页 Hero + KPI 卡片 |
| Steam 30% — 深色图表、数据密度 | ✅ 分析页 ECharts 图表 |
| Notion 20% — 排版呼吸感、信息层级 | ✅ PageShell + SectionHeader 分层 |
| Apple 10% — 毛玻璃顶栏、圆角 | ✅ TopNav `backdrop-filter: blur` |
| 禁止后台管理风格 | ✅ 无抽屉/面包屑/CRUD表格 |
| 禁止数据大屏/3D/发光边框 | ✅ 采纳 |
| Element Plus | ⚠️ 实际使用中，需注意不破坏设计风格 |

---

## 八、项目目录结构

```
BiliAnalysis/                        # 仓库根（不改名）
│
├── src/bilianalysis/                # Python 库（纯计算，不接触数据库）
│   ├── __init__.py
│   ├── models.py                    # 已有：Pydantic 领域模型
│   │
│   ├── crawler/                     # 已有：数据采集
│   │   ├── __init__.py
│   │   ├── api.py                   #   Bilibili API 封装
│   │   ├── pipeline.py              #   爬取编排
│   │   ├── storage.py               #   文件 I/O + 进度
│   │   └── signer.py                #   WBI 签名
│   │
│   ├── engine/                      # 已有：分析引擎
│   │   ├── __init__.py              #   create_engine 工厂
│   │   ├── base.py                  #   ABC + 报告模型
│   │   ├── pandas_engine.py         #   Pandas 实现
│   │   └── spark_engine.py          #   PySpark 实现
│   │
│   ├── scheduler/                   # 已有：调度框架
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── task.py
│   │   ├── registry.py
│   │   ├── runner.py
│   │   ├── cron_service.py
│   │   └── builtins/
│   │       ├── crawl_task.py
│   │       ├── clean_task.py
│   │       ├── stats_task.py
│   │       ├── cluster_task.py
│   │       └── predict_task.py
│   │
│   ├── config/                      # 已有：配置
│   │   ├── __init__.py
│   │   ├── model.py                 #   AppConfig Pydantic 模型
│   │   └── loader.py                #   YAML → AppConfig
│   │
│   ├── utils/                       # 已有：工具
│   │   ├── __init__.py
│   │   ├── fetch.py                 #   aiohttp 封装
│   │   └── ua.py                    #   UserAgent
│   │
│   ├── etl/                         # ★ 新增：数据转换（纯函数，不接触 DB）
│   │   ├── __init__.py
│   │   └── transform.py             #   raw JSON → 6 组 record dict
│   │
│   └── warehouse/                   # ★ 新增：数据仓库分层（纯计算）
│       ├── __init__.py
│       ├── dwd.py                   #   DWD 宽表构建
│       ├── dws.py                   #   DWS 汇总表
│       ├── ads.py                   #   ADS 应用表
│       └── keywords.py              #   内容特征分析
│
├── app/                             # 应用层（已有）
│   ├── api/                         #   FastAPI（部分完成）
│   │   ├── __init__.py
│   │   ├── app.py                   #   create_app 工厂
│   │   ├── deps.py                  #   依赖注入
│   │   ├── errors.py                #   异常体系
│   │   ├── schemas.py               #   响应模型
│   │   ├── router/
│   │   │   ├── __init__.py
│   │   │   ├── crawler.py           #   已有：POST/GET /api/crawler
│   │   │   ├── analysis.py          #   已有：POST/GET /api/analysis + /stats /clusters /predictions
│   │   │   ├── tasks.py             #   已有：GET /api/tasks + POST /api/tasks/{name}/run + history
│   │   │   └── config.py            #   已有：GET/PUT /api/config
│   │   ├── config.py                #   ★ 待新增：ApiSettings（含 database_url）
│   │   └── db/                      #   ★ 待新增：数据库访问层
│   │       ├── schema.py            #     SQLAlchemy ORM
│   │       ├── loader.py            #     DB 写入
│   │       └── queries.py           #     查询封装
│   │
│   └── ui/                          #   Vue3 前端（部分完成）
│       ├── package.json             #   Vue 3.5 + Element Plus + ECharts + Alova
│       ├── vite.config.ts
│       ├── vitest.config.ts
│       ├── playwright.config.ts
│       ├── index.html
│       ├── pnpm-lock.yaml
│       ├── tsconfig.json
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── router/index.ts
│       │   ├── types/api.ts
│       │   ├── styles/theme.css
│       │   ├── composables/
│       │   │   ├── useApi.ts
│       │   │   └── useChart.ts
│       │   ├── pages/
│       │   │   ├── HomePage.vue
│       │   │   └── analysis/
│       │   │       ├── StatsPage.vue
│       │   │       ├── ClusterPage.vue
│       │   │       └── PredictPage.vue
│       │   └── components/
│       │       ├── layout/          #   PageShell, TopNav
│       │       ├── home/            #   HeroSection, KpiCardRow, CategoryBar, CreatorTopList, TrendMiniChart
│       │       ├── analysis/        #   SubNavTabs, CategoryPanel, CreatorTable, ClusterCards, ForecastCards
│       │       ├── charts/          #   CategoryBarChart, TrendLineChart, ClusterScatter, FitLineChart
│       │       └── shared/          #   SectionHeader, StatCard
│       ├── e2e/                     #   Playwright 视觉回归
│       └── dist/                    #   构建产物
│
├── data/                            # 已有：运行时数据
│   ├── raw/         (*.json)
│   ├── processed/   (*.parquet)
│   └── reports/     (*.json)
│
├── docs/                            # 已有：文档
├── tests/                           # 已有：测试
├── design-demos/                    # 已有：设计原型
├── config.yaml                      # 已有：全局配置（crawler/analysis/data/scheduler）
└── pyproject.toml                   # 已有：uv 项目配置
```

**结构原则**：

- `src/bilianalysis/` 是纯 Python 库——计算、转换、文件 I/O、Parquet 读写。**不导入数据库驱动**
- `app/api/` 是 FastAPI 应用——已有骨架（crawler / analysis / tasks / config 4 组端点），待新增 PostgreSQL 集成
- `app/ui/` 是 Vue3 前端——已有 4 页面（首页/统计/聚类/预测），通过 Alova + HTTP 与 `app/api/` 通信
- 配置分离：`config.yaml`（全局—爬虫/引擎/调度）+ `app/api/config.py`（FastAPI 专属—数据库连接，待新增）

---

## 九、实施路线图

按依赖关系排序。已完成的标记 ✅。

### ✅ 阶段 1：FastAPI 骨架（已完成）

- [x] `app/api/app.py`——create_app 工厂
- [x] `app/api/deps.py`——依赖注入（config / runner / engine）
- [x] `app/api/errors.py`——AppError 异常体系
- [x] `app/api/schemas.py`——API 响应模型
- [x] 4 组 router：crawler / analysis / tasks / config

### ✅ 阶段 2：前端基础 + 分析页面（已完成）

- [x] Vite + Vue3 + TypeScript + TailwindCSS 脚手架
- [x] 首页（Hero + KPI 卡片 + 分区柱状图 + UP 主列表 + 趋势迷你图）
- [x] 统计页（基础统计 + 分区面板 + UP 主排行 + 周趋势图）
- [x] 聚类页（散点图 + 聚类卡片 + 特征重要性）
- [x] 预测页（拟合曲线 + 预测卡片）
- [x] Alova HTTP 封装 + ECharts composable
- [x] Vitest 单元测试 + Playwright e2e 视觉回归

### 阶段 3：库模块新增（2-3 天）

1. `src/bilianalysis/etl/transform.py`——raw JSON → 6 组 typed records（纯函数）
2. `src/bilianalysis/warehouse/dwd.py`——DWD 宽表构建
3. `src/bilianalysis/warehouse/dws.py`——DWS 三张汇总表
4. `src/bilianalysis/warehouse/ads.py`——ADS 应用表
5. `src/bilianalysis/warehouse/keywords.py`——内容特征分析
6. 写测试（纯函数测试，无需 mock 数据库）

### 阶段 4：PostgreSQL 集成（3-4 天）

1. `app/api/config.py`——ApiSettings（含 database_url）
2. `app/api/db/schema.py`——SQLAlchemy ORM 6 张表
3. `app/api/db/loader.py`——消费 `etl/transform.py` 产出的 records，写入 PG
4. `app/api/db/queries.py`——业务查询封装
5. 写集成测试（需要 PostgreSQL 容器）

### 阶段 5：业务 API 端点（2-3 天）

1. `app/api/router/videos.py`——GET /api/videos, GET /api/videos/{aid}
2. `app/api/router/creators.py`——GET /api/creators, GET /api/creators/{mid}
3. `app/api/router/weeks.py`——GET /api/weeks, GET /api/weeks/{number}
4. `app/api/router/categories.py`——GET /api/categories
5. 写集成测试

### 阶段 6：前端业务页面（4-5 天）

1. 视频库页（搜索 + 分区/周次筛选 + 卡片网格 + 分页）
2. 视频详情页（信息 + 互动数据 + 上榜记录）
3. UP 主榜 + UP 主详情页（统计 + 上榜视频列表）
4. 趋势分析页（播放/点赞率/投币率多线图 + 分区堆叠图）

### 阶段 7：调度器集成 + 部署（1-2 天）

1. 配置 Cron 定时任务：周一爬取 → 清洗 → 构建仓库 → 加载 PG
2. Docker Compose（PostgreSQL + API + 前端）
3. 更新 README + 课程演示准备

**剩余估算**：12-17 天（单人全职）。

---

## 十、关键设计决策总结

| # | 决策 | 理由 |
|----|------|------|
| 1 | 双轨数据流，不在引擎中硬插 PG | 保护已有 1133 行引擎代码，满足双重课程要求 |
| 2 | `src/bilianalysis/` 不接触数据库 | 库与应用职责分离，FastAPI 唯一持有 DB 连接 |
| 3 | ETL 拆分：库模块做转换，FastAPI 做加载 | 库模块保持纯函数无副作用，FastAPI 封装所有 DB I/O |
| 4 | 数据库配置在 `app/api/config.py`，非全局 YAML | DB 是 FastAPI 的私有依赖，不属于库模块 |
| 5 | Parquet + PostgreSQL 并存 | 用途不同：Parquet = 列式分析，PG = 行式查询 |
| 6 | 包名保持 `bilianalysis`，产品名用 BiliInsight | 零破坏性变更 |
| 7 | 分析引擎不动，在其输出之上建 DWD/DWS/ADS | 引擎已完整，数据仓库是增值层 |
| 8 | API 分析端点读文件而非读 PG | 引擎已产出结构化报告，走 PG 多一次无意义 ETL |
| 9 | 项目结构 `app/api/` + `app/ui/` | 应用层统一在 `app/` 下，与库 `src/` 清晰分离 |
| 10 | 不引入 Alembic | 6 张表结构稳定，DDL 在应用启动时直接执行 |
| 11 | 前端 TailwindCSS + 设计原型对齐 | 原型已验证设计方向，直接工程化 |
| 12 | 前端禁止后台管理风格，Element Plus 谨慎使用 | 产品定位内容发现。Element Plus 已引入但仅作辅助（表单/弹窗等），不套用其后台模板 |
| 13 | Python >= 3.13 | 已锁定，不降级 |
