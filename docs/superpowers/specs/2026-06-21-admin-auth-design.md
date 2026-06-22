# Admin API Key Authentication · Design

> 2026-06-21 | 单用户场景 | API Key 方案

## 问题

BiliInsight 有 6 个完全无保护的写端点，任何能访问 API 服务器的人都可以触发爬虫、运行分析流水线、写入数据库、修改运行时配置：

| 端点 | 影响 |
|------|------|
| `POST /api/crawler` | 触发爬虫 |
| `POST /api/analysis` | 触发分析流水线 |
| `POST /api/tasks/{name}/run` | 触发任意流水线 |
| `POST /api/task/{name}` | 运行单个任务 |
| `POST /api/db/load` | 写入 PostgreSQL |
| `PUT /api/config` | 修改运行时配置 + 覆写 config.yaml |

当前零认证基础设施：无用户表、无 token、无中间件、无前端路由守卫、CORS 全开。

## 方案：API Key + Header 校验

单用户场景，不需要账号体系。管理员持有 API Key，所有写请求通过 `X-API-Key` header 传递。

### 架构

```
.env / 环境变量                    ← ADMIN_API_KEY 来源
    │
app/api/config.py → ApiSettings    ← admin_api_key 字段
    │
app/api/app.py 启动时              ← 空则自动生成 32 字节随机 key
    │
app/api/deps.py → require_admin()  ← secrets.compare_digest 校验
    │
6 个路由端点 Depends(require_admin) ← 写操作注入
    │
前端 useApi.ts beforeRequest       ← 自动带 X-API-Key header
    │
AdminPage.vue key 输入栏           ← 用户配置入口
```

### 后端

**config.py** — `ApiSettings` 新增字段：

```python
admin_api_key: str = ""
```

**app.py** — 启动行为：

```python
settings = ApiSettings()
if not settings.admin_api_key:
    settings.admin_api_key = secrets.token_urlsafe(32)
    print(f"[admin] Auto-generated API key: {settings.admin_api_key}")
app.state.api_settings = settings
```

**deps.py** — 认证依赖：

```python
import secrets
from fastapi import Request, HTTPException

def require_admin(request: Request) -> None:
    expected = request.app.state.api_settings.admin_api_key
    provided = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API Key")
```

全局生效，无环境豁免。`admin_api_key` 为空时 `compare_digest("", "...")` 一定不匹配 → 401。

**6 个路由文件** — 各加一行 `Depends(require_admin)`：

- `app/api/router/crawler.py` — `POST /api/crawler`
- `app/api/router/analysis.py` — `POST /api/analysis`
- `app/api/router/tasks.py` — `POST /api/tasks/{name}/run`, `POST /api/task/{name}`
- `app/api/router/db_load.py` — `POST /api/db/load`
- `app/api/router/config.py` — `PUT /api/config`

签名模式（以 crawler 为例）：

```python
async def trigger_crawl(
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[CrawlRunner, Depends(get_crawl_runner)],
    request: Request,
    _admin: None = Depends(require_admin),   # ← 新加
):
```

GET 端点不改。

### 前端

**useApi.ts** — `beforeRequest` hook 自动注入 header：

```ts
beforeRequest: (config) => {
  const key = localStorage.getItem("admin_api_key")
  if (key && config.method !== 'GET') {
    config.headers = { ...config.headers, 'X-API-Key': key }
  }
}
```

仅 POST/PUT 请求带 header，GET 不泄露 key。

**AdminPage.vue** — 新增 key 输入栏：

- 页面顶部蓝色提示栏
- 输入框 `type="password"`，已保存时显示占位符
- 保存按钮写入 `localStorage("admin_api_key", value)`
- 状态指示：绿色「已配置」/ 红色「未配置 — 写操作不可用」
- 未配置时所有触发按钮灰态 + tooltip

### 变更清单

| 文件 | 改动类型 | 内容 |
|------|---------|------|
| `app/api/config.py` | 修改 | 新增 `admin_api_key: str` 字段 |
| `app/api/app.py` | 修改 | 挂载 ApiSettings 到 app.state，空 key 自动生成 |
| `app/api/deps.py` | 修改 | 新增 `require_admin()` 依赖函数 |
| `app/api/router/crawler.py` | 修改 | POST 端点加 `Depends(require_admin)` |
| `app/api/router/analysis.py` | 修改 | POST 端点加 `Depends(require_admin)` |
| `app/api/router/tasks.py` | 修改 | 2 个 POST 端点加 `Depends(require_admin)` |
| `app/api/router/db_load.py` | 修改 | POST 端点加 `Depends(require_admin)` |
| `app/api/router/config.py` | 修改 | PUT 端点加 `Depends(require_admin)` |
| `app/ui/src/composables/useApi.ts` | 修改 | 新增 `beforeRequest` hook 注入 X-API-Key |
| `app/ui/src/pages/AdminPage.vue` | 修改 | 新增 key 输入栏 + 未配置时按钮灰态 |

### 不涉及

- 用户表、密码哈希、JWT
- 路由守卫、登录页面
- Nginx 层认证
- 只读 / GET 端点
- Docker Compose 修改（ADMIN_API_KEY 环境变量已自然支持）

### 开发体验

- `uv run bilianalysis serve` — 控制台打印自动生成的 key，复制到前端输入框即可
- Docker 部署 — `docker-compose.yml` environment 注入 `ADMIN_API_KEY`
- 测试 — `admin_api_key=""` 的 `ApiSettings` 配合 `TestClient`，手动设 header

### 安全考虑

- `secrets.compare_digest` 防 timing attack
- Key 仅通过 POST/PUT header 传输（非 URL query）
- 前端 localStorage 存储（单用户场景可接受）
