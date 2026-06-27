# BiliInsight

B 站"每周必看"内容洞察平台。爬取 Bilibili API 数据，通过 Spark Connect + PySpark 分析引擎进行数据处理、统计、聚类、预测和关键词提取，FastAPI + Vue3 构建前后端，PostgreSQL 存储。

## 技术栈

| 层 | 技术 |
|---|------|
| 爬虫 | aiohttp, Bilibili WBI 签名 |
| 分析引擎 | PySpark 4.1.2 (Spark Connect), pandas, jieba, scikit-learn |
| 后端 | FastAPI, SQLAlchemy (async), PostgreSQL |
| 前端 | Vue 3, ECharts, Element Plus, Pinia, Alova, Tailwind CSS |
| 存储 | HDFS, Parquet |
| 调度 | 内置 cron 服务 |

## 快速开始

```bash
# 1. 安装依赖
uv sync
cd app/ui && pnpm install && cd ../..

# 2. 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml 选择引擎（pandas | spark）

# 3. 启动后端
uv run bilianalysis serve --port 8080

# 4. 启动前端 (另一个终端)
cd app/ui && pnpm dev
```

打开 http://localhost:5173

## 架构

```
app/
├── api/              FastAPI 应用 + 路由 + 数据库
├── cli/              Typer CLI (serve, schedule)
└── ui/               Vue3 前端

src/bilianalysis/
├── crawler/          B 站爬虫 (WBI 签名, 反爬)
├── engine/           分析引擎
│   ├── pandas_engine.py    Pandas 本地引擎
│   ├── spark_engine.py     Spark Connect 远程引擎
│   └── spark/              Spark 4.1.2 分析模块
│       ├── clean.py
│       └── analysis.py
├── config/           配置模型
├── nlp/              jieba TF-IDF 关键词提取
├── warehouse/        数仓 (DWD/DWS/ADS)
└── scheduler/        流水线调度
```

## 引擎模式

### Pandas (本地)

```yaml
analysis:
  engine: pandas
```

所有计算在本地完成，数据存储在本地文件系统。

### Spark (远程)

```yaml
analysis:
  engine: spark
  spark_remote: "sc://host:15002"
  webhdfs_url: "http://host:9870"
```

通过 gRPC 连接远程 Spark Connect 服务端，数据存储在 HDFS `/user/hadoop/bilibili/`。启动时自动检查 Spark 和 HDFS 连通性。

## 分析流水线

| 步骤 | 说明 |
|------|------|
| `crawl` | 爬取 B 站每周必看 JSON |
| `clean_data` | JSON → 5 张 Parquet 表 |
| `statistics` | 整体 / 分区 / UP 主 / 周统计 |
| `clustering` | KMeans(k=3) 视频分群 |
| `prediction` | 周级播放量线性回归 + 未来 4 期预测 |
| `keywords` | jieba TF-IDF 全局/周/分区关键词 |
| `build_warehouse` | DWD/DWS/ADS 数仓构建 |
| `db_load` | 数据入库 PostgreSQL |

通过 Admin 页面或 API 触发流水线。分析页面读取本地 JSON 缓存，毫秒级响应。

## 用户认证

Session Cookie 登录，管理员 + 匿名用户双角色。管理员初始凭据在配置文件中，首次登录强制修改密码，之后走数据库验证。

```yaml
# .env 或环境变量
ADMIN_USER=admin
ADMIN_PASSWORD=admin
```

匿名用户可浏览全部数据看板，管理员可触发任务和管理配置。

## API

| 端点 | 说明 | 权限 |
|------|------|------|
| `GET  /api/analysis/stats` | 统计报告 | 匿名 |
| `GET  /api/analysis/clusters` | 聚类报告 | 匿名 |
| `GET  /api/analysis/predictions` | 预测报告 | 匿名 |
| `GET  /api/analysis/keywords` | 关键词报告 | 匿名 |
| `POST /api/task/{name}` | 触发单个任务 | 管理员 |
| `POST /api/tasks/{name}/run` | 触发流水线 | 管理员 |
| `GET  /api/tasks/running` | 运行中任务 | 管理员 |
| `GET  /api/tasks/history` | 执行历史 | 管理员 |
| `POST /api/auth/login` | 登录 | 无 |
| `POST /api/auth/logout` | 退出 | 登录 |
| `GET  /api/auth/me` | 当前用户 | 登录 |

## 前端页面

| 路由 | 页面 |
|------|------|
| `/` | 首页 |
| `/videos` | 视频库 (搜索/排序/筛选) |
| `/videos/:aid` | 视频详情 |
| `/weeks` | 周报列表 |
| `/weeks/:number` | 周报详情 |
| `/creators` | 创作者 |
| `/creators/:mid` | 创作者详情 |
| `/categories` | 分区 |
| `/analysis/stats` | 统计分析 |
| `/analysis/clusters` | 聚类分析 |
| `/analysis/predictions` | 预测分析 |
| `/analysis/keywords` | 内容洞察 |
| `/analysis/models` | 模型对比 |
| `/admin` | 管理后台 |
| `/login` | 登录 |

## 命令行

```bash
# 启动服务
bilianalysis serve --port 8080

# 调度器
bilianalysis schedule list              # 列出所有流水线
bilianalysis schedule run -p analysis   # 手动触发流水线
bilianalysis schedule run-task -t crawl # 触发单个任务
bilianalysis schedule check-raw         # 检查本地 vs HDFS 文件同步

# 测试
bilianalysis schedule test -p analysis  # 验证流水线配置
```

## 测试

```bash
uv run pytest tests/ -v          # 148 后端测试
cd app/ui && pnpm test:unit      # 前端单元测试
cd app/ui && pnpm test:e2e       # E2E 测试
```

## 依赖

- Python 3.11
- JDK 17+ (Spark Connect 服务端)
- PostgreSQL (数据库)
- Hadoop 3.5.x / Spark 4.1.2 (Spark 模式)
- Node.js 18+ (前端)
