# Admin API Key Authentication · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect 6 write endpoints with X-API-Key header authentication, configurable via .env / environment variable.

**Architecture:** `ApiSettings` gains `admin_api_key` field → `app.py` auto-generates if empty → `deps.py` adds `require_admin()` dependency → 6 route files inject `Depends(require_admin)` → frontend `useApi.ts` attaches header from localStorage → `AdminPage.vue` provides key input UI.

**Tech Stack:** FastAPI dependencies, Python `secrets` module, localStorage, Alova `beforeRequest` hook.

---

### Task 1: Add `admin_api_key` field to ApiSettings

**Files:**
- Modify: `app/api/config.py`

- [ ] **Step 1: Add the field**

```python
# app/api/config.py — insert after database_pool_size
class ApiSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/biliinsight"
    database_pool_size: int = 5
    admin_api_key: str = ""

    model_config = {"env_file": ".env"}
```

- [ ] **Step 2: Verify the field loads from .env**

Run:
```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "
from api.config import ApiSettings
s = ApiSettings()
print('admin_api_key:', repr(s.admin_api_key))
print('database_url:', repr(s.database_url))
"
```

Expected: `admin_api_key: ''` (default), `database_url` unchanged.

- [ ] **Step 3: Commit**

```bash
git add app/api/config.py
git commit -m "feat: add admin_api_key field to ApiSettings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Add `require_admin` dependency to deps.py

**Files:**
- Modify: `app/api/deps.py`

- [ ] **Step 1: Add the dependency function**

```python
# app/api/deps.py — append after get_engine()
import secrets
from fastapi import Request, HTTPException


def require_admin(request: Request) -> None:
    """Validate X-API-Key header against configured admin_api_key.

    Raises 401 if the header is missing or doesn't match.
    """
    expected = request.app.state.api_settings.admin_api_key
    provided = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: invalid or missing API Key",
        )
```

The existing `from fastapi import Request, Depends` import at line 4 already covers `Request`. Add `import secrets` and `from fastapi import ... HTTPException` to the top imports:

```python
# app/api/deps.py — replace the fastapi import line (line 4)
import secrets
from fastapi import Request, Depends, HTTPException
```

- [ ] **Step 2: Verify import works**

```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "from api.deps import require_admin; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add require_admin dependency for API key validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Mount ApiSettings in app.py and auto-generate key

**Files:**
- Modify: `app/api/app.py`

- [ ] **Step 1: Instantiate ApiSettings and auto-generate key**

In `create_app()`, before `app = FastAPI(...)`:

```python
# app/api/app.py — after imports, inside create_app(), before the FastAPI() call
def create_app(config: AppConfig) -> FastAPI:
    # ... existing lifespan ...

    # Init API settings — auto-generate admin key if not configured
    from api.config import ApiSettings
    api_settings = ApiSettings()
    if not api_settings.admin_api_key:
        import secrets
        api_settings.admin_api_key = secrets.token_urlsafe(32)
        print(f"[admin] Auto-generated API key: {api_settings.admin_api_key}")

    app = FastAPI(title="BiliAnalysis API", version="0.1.0", lifespan=_lifespan)

    app.state.api_settings = api_settings
    # ... rest unchanged ...
```

- [ ] **Step 2: Verify app starts with auto-generated key**

```bash
cd D:/Desktop/BiliAnalysis && timeout 3 uv run python -c "
from api.config import ApiSettings
from bilianalysis.config.model import AppConfig
from api.app import create_app
import os
os.environ['ADMIN_API_KEY'] = ''
app = create_app(AppConfig())
key = app.state.api_settings.admin_api_key
assert len(key) >= 32, f'Key too short: {len(key)}'
print(f'Key generated: {key[:8]}... ({len(key)} chars)')
" 2>&1 || true
```

Expected: Prints the auto-generated key with `[admin]` prefix.

- [ ] **Step 3: Commit**

```bash
git add app/api/app.py
git commit -m "feat: auto-generate admin API key on startup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Protect 6 write endpoints with `Depends(require_admin)`

**Files:**
- Modify: `app/api/router/crawler.py`
- Modify: `app/api/router/analysis.py`
- Modify: `app/api/router/tasks.py`
- Modify: `app/api/router/db_load.py`
- Modify: `app/api/router/config.py`

- [ ] **Step 1: crawler.py — POST /api/crawler**

Add import and dependency to `trigger_crawl`:

```python
# app/api/router/crawler.py — change the import line
from api.deps import get_config, require_admin

# and in the function signature, add the dependency parameter:
@router.post("/crawler", status_code=202, response_model=TaskTriggerResponse)
async def trigger_crawl(
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    _admin: None = Depends(require_admin),
):
```

- [ ] **Step 2: analysis.py — POST /api/analysis**

```python
# app/api/router/analysis.py — change the import line
from api.deps import get_config, get_runner, get_engine, require_admin

# and in trigger_analysis signature:
@router.post("/analysis", status_code=202, response_model=TaskTriggerResponse)
async def trigger_analysis(
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[PipelineRunner, Depends(get_runner)],
    request: Request,
    _admin: None = Depends(require_admin),
):
```

- [ ] **Step 3: tasks.py — POST /api/tasks/{name}/run and POST /api/task/{name}**

```python
# app/api/router/tasks.py — change the import line
from api.deps import get_config, get_runner, require_admin

# in trigger_pipeline signature:
@router.post("/tasks/{name}/run", status_code=202, response_model=TaskTriggerResponse)
async def trigger_pipeline(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    runner: Annotated[PipelineRunner, Depends(get_runner)],
    request: Request,
    _admin: None = Depends(require_admin),
):

# in run_single_task signature:
@router.post("/task/{name}", status_code=202, response_model=TaskTriggerResponse)
async def run_single_task(
    name: str,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    _admin: None = Depends(require_admin),
):
```

- [ ] **Step 4: db_load.py — POST /api/db/load**

```python
# app/api/router/db_load.py — change the import line
from api.deps import get_config, get_db, require_admin

# in load_to_db signature:
@router.post("/db/load")
async def load_to_db(
    config: Annotated[AppConfig, Depends(get_config)],
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: None = Depends(require_admin),
):
```

- [ ] **Step 5: config.py router — PUT /api/config**

```python
# app/api/router/config.py — change the import line
from api.deps import get_config, require_admin

# in update_config signature:
@router.put("/config")
async def update_config(
    body: ConfigUpdateRequest,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    _admin: None = Depends(require_admin),
):
```

- [ ] **Step 6: Verify all imports and run tests**

```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "
from api.router.crawler import router as r1
from api.router.analysis import router as r2
from api.router.tasks import router as r3
from api.router.db_load import router as r4
from api.router.config import router as r5
print('All routers import OK')
" && uv run pytest tests/test_api.py -v --tb=short 2>&1 | tail -20
```

Expected: All routers import OK, tests run. Note: existing tests may fail with 401 on POST/PUT endpoints — this is expected and will be fixed in Task 5.

- [ ] **Step 7: Commit**

```bash
git add app/api/router/crawler.py app/api/router/analysis.py app/api/router/tasks.py app/api/router/db_load.py app/api/router/config.py
git commit -m "feat: protect 6 write endpoints with require_admin dependency

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Update tests to work with auth

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add an authenticated client fixture**

In `tests/test_api.py`, add after the existing `client` fixture (line 13):

```python
@pytest.fixture
def auth_client():
    """A TestClient with admin_api_key configured and X-API-Key header set."""
    import os
    os.environ["ADMIN_API_KEY"] = "test-key-123"
    config = AppConfig()
    app = create_app(config)
    client = TestClient(app)
    client.headers["X-API-Key"] = "test-key-123"
    return client
```

- [ ] **Step 2: Update existing tests that use POST/PUT to use `auth_client`**

Tests `test_config_put_valid`, `test_config_put_invalid_section`, `test_config_put_invalid_field` in `TestHealthAndConfig` — change the fixture from `client` to `auth_client`:

```python
class TestHealthAndConfig:
    def test_config_get(self, client):
        # GET — no auth needed, uses existing 'client'
        ...

    def test_config_put_valid(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "crawler",
            "values": {"request_delay": 5.0},
            "persist": False,
        })
        assert resp.status_code == 200
        assert resp.json()["persisted"] is False

    def test_config_put_invalid_section(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "nonexistent",
            "values": {},
            "persist": False,
        })
        assert resp.status_code == 400

    def test_config_put_invalid_field(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "crawler",
            "values": {"nonexistent_field": 123},
            "persist": False,
        })
        assert resp.status_code == 400
```

- [ ] **Step 3: Add auth-specific tests**

Add a new test class at the end of `tests/test_api.py`:

```python
class TestAdminAuth:
    def test_post_without_key_returns_401(self, client):
        """Any POST endpoint without X-API-Key returns 401."""
        resp = client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["detail"]

    def test_post_with_wrong_key_returns_401(self, auth_client):
        """Wrong key returns 401."""
        auth_client.headers["X-API-Key"] = "wrong-key"
        resp = auth_client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 401

    def test_get_endpoints_unaffected(self, client):
        """GET endpoints are not protected."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        resp = client.get("/api/crawler")
        assert resp.status_code == 200
        resp = client.get("/api/tasks")
        assert resp.status_code == 200

    def test_config_get_unaffected(self, client):
        """GET /api/config still works without auth."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        assert "crawler" in resp.json()
```

- [ ] **Step 4: Run all tests**

```bash
cd D:/Desktop/BiliAnalysis && uv run pytest tests/test_api.py -v --tb=short
```

Expected: All tests pass (new + existing).

- [ ] **Step 5: Commit**

```bash
git add tests/test_api.py
git commit -m "test: update API tests for admin auth and add auth-specific tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Frontend — inject X-API-Key header in useApi.ts

**Files:**
- Modify: `app/ui/src/composables/useApi.ts`

- [ ] **Step 1: Add beforeRequest hook to the alova instance**

The alova instance is created at line 16 of `useApi.ts`. Add a `beforeRequest` hook inside the `createAlova({...})` call:

```typescript
const alova = createAlova({
  baseURL: '/api',
  statesHook: vueHook,
  requestAdapter: adapterFetch(),
  beforeRequest: (config) => {
    const key = localStorage.getItem("admin_api_key")
    if (key && config.method !== 'GET') {
      config.headers = { ...config.headers, 'X-API-Key': key }
    }
  },
  responded: {
    onSuccess: async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(
          (body as { detail?: string }).detail ?? `HTTP ${response.status}`,
        )
      }
      return response.json()
    },
  },
})
```

Note: The `beforeRequest` hook is a standard Alova feature. Import for `config.method` is already available through the Alova method object.

- [ ] **Step 2: Verify frontend build**

```bash
cd D:/Desktop/BiliAnalysis/app/ui && pnpm build 2>&1 | grep -E "(error|✓ built|useApi)" | head -5
```

Expected: `✓ built in X.XXs`, no errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/composables/useApi.ts
git commit -m "feat: auto-inject X-API-Key header for write requests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Frontend — add API Key input to AdminPage.vue

**Files:**
- Modify: `app/ui/src/pages/AdminPage.vue`

- [ ] **Step 1: Add script state and methods**

In the `<script setup>` block, after the existing imports, add:

```typescript
// ── API Key ──
const apiKeyInput = ref('')
const apiKeySaved = ref(!!localStorage.getItem("admin_api_key"))

function saveApiKey() {
  if (apiKeyInput.value.trim()) {
    localStorage.setItem("admin_api_key", apiKeyInput.value.trim())
    apiKeySaved.value = true
    apiKeyInput.value = ''
  }
}

function clearApiKey() {
  localStorage.removeItem("admin_api_key")
  apiKeySaved.value = false
}
```

- [ ] **Step 2: Add the UI bar in the template**

Insert after the `<h1>` title block (after line 126 in original), before "系统状态":

```html
    <!-- ── API Key 配置 ── -->
    <div class="mb-6 p-4 rounded-[12px] border flex items-center gap-3 flex-wrap"
         :class="apiKeySaved
           ? 'bg-[#ECFDF5] border-[#A7F3D0]'
           : 'bg-[#E6F7FD] border-[#7DD3FC]'">
      <span class="text-sm font-semibold shrink-0"
            :class="apiKeySaved ? 'text-[#166534]' : 'text-[#0369A1]'">
        🔑 API Key
      </span>
      <template v-if="apiKeySaved">
        <span class="text-sm text-[#166534] font-medium">已配置</span>
        <span class="inline-block w-2 h-2 rounded-full bg-[#22C55E]" />
        <button
          @click="clearApiKey"
          class="ml-auto px-3 py-1.5 text-xs font-medium rounded-lg border-none cursor-pointer
                 bg-white/60 text-[#991B1B] hover:bg-[#FEF2F2] transition-colors"
        >
          清除
        </button>
      </template>
      <template v-else>
        <input
          v-model="apiKeyInput"
          type="password"
          placeholder="粘贴 API Key…"
          class="flex-1 min-w-[200px] px-3 py-2 rounded-lg border border-[#7DD3FC] bg-white
                 text-sm outline-none focus:ring-2 focus:ring-blue/30 transition-shadow"
          @keyup.enter="saveApiKey"
        />
        <button
          @click="saveApiKey"
          :disabled="!apiKeyInput.trim()"
          class="px-4 py-2 rounded-lg text-sm font-semibold border-none cursor-pointer
                 bg-blue text-white hover:brightness-90 transition-all
                 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          保存
        </button>
      </template>
    </div>
```

- [ ] **Step 3: Make trigger buttons disabled when no key**

Change the `:disabled` attribute on pipeline trigger buttons (around line 171) from:

```html
:disabled="actionLoading !== ''"
```

to:

```html
:disabled="actionLoading !== '' || !apiKeySaved"
:title="!apiKeySaved ? '请先配置 API Key' : ''"
```

And on individual task buttons (around line 198):

```html
:disabled="actionLoading !== '' || !apiKeySaved"
:title="!apiKeySaved ? '请先配置 API Key' : ''"
```

- [ ] **Step 4: Verify build**

```bash
cd D:/Desktop/BiliAnalysis/app/ui && npx vue-tsc --noEmit 2>&1 && pnpm build 2>&1 | grep -E "(error|✓ built)" | head -3
```

Expected: no type errors, `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/pages/AdminPage.vue
git commit -m "feat: add API Key configuration UI to AdminPage

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Verification (after all tasks)

```bash
# Backend: all tests pass
cd D:/Desktop/BiliAnalysis && uv run pytest tests/ -v --tb=short 2>&1 | tail -5

# Frontend: type-check + build
cd D:/Desktop/BiliAnalysis/app/ui && npx vue-tsc --noEmit && pnpm build 2>&1 | grep "✓ built"

# Smoke test: start server, verify 401 without key
# (manual step) uv run bilianalysis serve --port 8080
# curl -X POST http://localhost:8080/api/crawler → 401
# curl -X POST http://localhost:8080/api/crawler -H "X-API-Key: <key>" → 202
```
