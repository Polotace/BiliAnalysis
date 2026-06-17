# 数据采集模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Bilibili "每周必看" 数据采集模块：重写 fetch.py 为函数式设计，新建 api.py/storage.py/pipeline.py，支持顺序/并发爬取、重试、断点续爬、增量更新。

**Architecture:** 4 层管道 — fetch.py（HTTP 传输）→ api.py（API 封装）→ pipeline.py（编排限速重试）→ storage.py（文件持久化）。Session 由调用方显式创建注入，Pydantic 建模配置与报告。

**Tech Stack:** Python 3.13, aiohttp, fake-useragent, pydantic, pytest + pytest-asyncio

---

## 文件结构

```
修改: src/utils/fetch.py        # 重写为函数式 HTTP 工具
保留: src/utils/ua.py           # 不变
新建: src/crawler/__init__.py   # 包初始化（已存在但为空）
新建: src/crawler/api.py        # Bilibili API 封装
新建: src/crawler/storage.py    # JSON 存取 + progress 管理
新建: src/crawler/pipeline.py   # 爬取编排 + Pydantic 模型

新建: tests/test_fetch.py       # fetch.py 单元测试
新建: tests/test_api.py         # api.py 单元测试
新建: tests/test_storage.py     # storage.py 单元测试
新建: tests/test_pipeline.py    # pipeline.py 单元测试
```

### 依赖目标

| 模块 | 依赖 |
|------|------|
| fetch.py | aiohttp, fake-useragent (已有) |
| api.py | fetch.py |
| storage.py | 无外部依赖（标准库 json/pathlib + asyncio） |
| pipeline.py | api.py, storage.py, pydantic (新增) |

---

### Task 1: 添加 pydantic 依赖并配置 pytest

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pydantic**

Run: `uv add pydantic`

- [ ] **Step 2: Add pytest-asyncio**

Run: `uv add --dev pytest pytest-asyncio`

- [ ] **Step 3: Add pytest config to pyproject.toml**

Edit `pyproject.toml`, append after `[project]` section:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Verify install**

Run: `uv run python -c "import pydantic; print(pydantic.__version__)"`
Expected: version string printed

Run: `uv run pytest --version`
Expected: pytest version printed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pydantic and pytest-asyncio dependencies"
```

---

### Task 2: 重写 fetch.py

**Files:**
- Modify: `src/utils/fetch.py`
- Create: `tests/test_fetch.py`

#### Step 1: Write tests for HttpError

Create `tests/test_fetch.py`:

```python
import pytest
from bilianalysis.utils.fetch import HttpError


class TestHttpError:
    def test_http_error_has_status_and_message(self):
        err = HttpError(404, "Not Found")
        assert err.status == 404
        assert err.message == "Not Found"
        assert str(err) == "[404] Not Found"

    def test_http_error_default_message(self):
        err = HttpError(500)
        assert err.status == 500
        assert "500" in str(err)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fetch.py -v`
Expected: FAIL — `HttpError` not defined

#### Step 3: Write HttpError class

Replace `src/utils/fetch.py`:

```python
"""异步 HTTP 工具模块。函数式设计，Session 由调用方显式管理。"""
import aiohttp
from bilianalysis.utils import ua

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=3)


class HttpError(Exception):
    """HTTP 请求失败异常"""

    def __init__(self, status: int, message: str = ""):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}" if message else f"[{status}]")


def create_session(timeout: aiohttp.ClientTimeout | None = None) -> aiohttp.ClientSession:
    """创建预配置 Session：自动注入随机 UA header + 超时"""
    headers = {"User-Agent": ua.random}
    return aiohttp.ClientSession(headers=headers, timeout=timeout or DEFAULT_TIMEOUT)


async def get(session: aiohttp.ClientSession, url: str,
              headers: dict | None = None) -> dict | list | str:
    """GET 请求。JSON 响应自动解析为 dict/list；非 JSON 返回文本。失败抛 HttpError。"""
    req_headers = {}
    if headers:
        req_headers.update(headers)
    try:
        async with session.get(url, headers=req_headers or None) as resp:
            if resp.status == 200:
                content_type = resp.content_type or ""
                if "application/json" in content_type:
                    return await resp.json()
                return await resp.text()
            raise HttpError(resp.status, await resp.text())
    except aiohttp.ClientError as e:
        raise HttpError(0, str(e))


async def post(session: aiohttp.ClientSession, url: str,
               data: dict | None = None,
               json: dict | None = None,
               headers: dict | None = None) -> dict | list | str:
    """POST 请求。JSON 响应自动解析为 dict/list；非 JSON 返回文本。失败抛 HttpError。"""
    req_headers = {}
    if headers:
        req_headers.update(headers)
    try:
        async with session.post(url, data=data, json=json,
                                headers=req_headers or None) as resp:
            if resp.status == 200:
                content_type = resp.content_type or ""
                if "application/json" in content_type:
                    return await resp.json()
                return await resp.text()
            raise HttpError(resp.status, await resp.text())
    except aiohttp.ClientError as e:
        raise HttpError(0, str(e))
```

- [ ] **Step 4: Run HttpError tests to verify pass**

Run: `uv run pytest tests/test_fetch.py::TestHttpError -v`
Expected: PASS

#### Step 5: Write tests for create_session, get, post

Append to `tests/test_fetch.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from bilianalysis.utils.fetch import create_session, get, post, HttpError, DEFAULT_TIMEOUT


class TestCreateSession:
    def test_returns_client_session(self):
        session = create_session()
        assert isinstance(session, aiohttp.ClientSession)

    def test_uses_default_timeout(self):
        session = create_session()
        assert session.timeout == DEFAULT_TIMEOUT

    def test_custom_timeout(self):
        custom = aiohttp.ClientTimeout(total=5, connect=1)
        session = create_session(timeout=custom)
        assert session.timeout == custom


class TestGet:
    @pytest.mark.asyncio
    async def test_get_json_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"code": 0, "data": [1, 2, 3]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        result = await get(mock_session, "https://example.com/api")
        assert result == {"code": 0, "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_get_text_response(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "text/html"
        mock_resp.text = AsyncMock(return_value="<html>ok</html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        result = await get(mock_session, "https://example.com")
        assert result == "<html>ok</html>"

    @pytest.mark.asyncio
    async def test_get_non_200_raises_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.text = AsyncMock(return_value="not found")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with pytest.raises(HttpError) as exc_info:
            await get(mock_session, "https://example.com/missing")
        assert exc_info.value.status == 404

    @pytest.mark.asyncio
    async def test_get_network_error_raises_http_error(self):
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("connection refused"))

        with pytest.raises(HttpError) as exc_info:
            await get(mock_session, "https://example.com")
        assert exc_info.value.status == 0
        assert "connection refused" in exc_info.value.message


class TestPost:
    @pytest.mark.asyncio
    async def test_post_json_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"result": "ok"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        result = await post(mock_session, "https://example.com/api", json={"key": "val"})
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_post_non_200_raises_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="server error")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        with pytest.raises(HttpError) as exc_info:
            await post(mock_session, "https://example.com/api")
        assert exc_info.value.status == 500
```

- [ ] **Step 6: Run all fetch tests**

Run: `uv run pytest tests/test_fetch.py -v`
Expected: All 10 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/utils/fetch.py tests/test_fetch.py
git commit -m "refactor: rewrite fetch.py as functional HTTP utility with HttpError"
```

---

### Task 3: 创建 api.py

**Files:**
- Create: `src/crawler/api.py`
- Create: `tests/test_api.py`

#### Step 1: Write tests for api.py

Create `tests/test_api.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bilianalysis.crawler import list_series, get_weekly_videos, BASE_URL
from bilianalysis.utils.fetch import HttpError

SERIES_LIST_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "list": [
            {"number": 1, "subject": "第一期", "name": "每周必看 01"},
            {"number": 2, "subject": "第二期", "name": "每周必看 02"},
            {"number": 3, "subject": "第三期", "name": "每周必看 03"},
        ]
    }
}

SERIES_ONE_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "config": {"number": 1, "subject": "测试期", "name": "每周必看 01"},
        "list": [
            {"aid": 123, "title": "测试视频", "owner": {"mid": 1, "name": "UP主"},
             "stat": {"view": 1000, "like": 50}}
        ]
    }
}


class TestListSeries:
    @pytest.mark.asyncio
    async def test_returns_series_list(self):
        with patch("src.crawler.api.get", AsyncMock(return_value=SERIES_LIST_RESPONSE)):
            result = await list_series(MagicMock())
        assert len(result) == 3
        assert result[0]["number"] == 1
        assert result[-1]["number"] == 3

    @pytest.mark.asyncio
    async def test_calls_correct_url(self):
        mock_get = AsyncMock(return_value=SERIES_LIST_RESPONSE)
        with patch("src.crawler.api.get", mock_get):
            await list_series(MagicMock())
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0]
        assert call_args[1] == f"{BASE_URL}/list"


class TestGetWeeklyVideos:
    @pytest.mark.asyncio
    async def test_returns_data_dict(self):
        with patch("src.crawler.api.get", AsyncMock(return_value=SERIES_ONE_RESPONSE)):
            result = await get_weekly_videos(MagicMock(), 1)
        assert result["config"]["number"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_url_includes_number(self):
        mock_get = AsyncMock(return_value=SERIES_ONE_RESPONSE)
        with patch("src.crawler.api.get", mock_get):
            await get_weekly_videos(MagicMock(), 42)
        call_args = mock_get.call_args[0]
        assert "number=42" in call_args[1]

    @pytest.mark.asyncio
    async def test_propagates_http_error(self):
        err = HttpError(502, "bad gateway")
        mock_get = AsyncMock(side_effect=err)
        with patch("src.crawler.api.get", mock_get):
            with pytest.raises(HttpError) as exc_info:
                await get_weekly_videos(MagicMock(), 1)
            assert exc_info.value.status == 502
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — module not found

#### Step 3: Write api.py

Create `src/crawler/api.py`:

```python
"""Bilibili "每周必看" API 封装。"""
import aiohttp
from bilianalysis.utils.fetch import get

BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"


async def list_series(session: aiohttp.ClientSession) -> list[dict]:
    """获取所有期数列表。返回 data.list，按 number 升序排列。"""
    url = f"{BASE_URL}/list"
    resp = await get(session, url)
    items = resp.get("data", {}).get("list", [])
    items.sort(key=lambda x: x.get("number", 0))
    return items


async def get_weekly_videos(session: aiohttp.ClientSession,
                            number: int) -> dict:
    """获取指定期数的完整数据。返回 API 原始 data 字典 {config, list}。
       HttpError 直接透传，由 pipeline 层捕获处理。"""
    url = f"{BASE_URL}/one?number={number}"
    resp = await get(session, url)
    return resp.get("data", {})
```

- [ ] **Step 4: Run api tests**

Run: `uv run pytest tests/test_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/crawler/__init__.py src/crawler/api.py tests/test_api.py
git commit -m "feat: add Bilibili weekly series API client"
```

---

### Task 4: 创建 storage.py

**Files:**
- Create: `src/crawler/storage.py`
- Create: `tests/test_storage.py`

#### Step 1: Write tests for storage.py

Create `tests/test_storage.py`:

```python
import json
import pytest
from pathlib import Path
from bilianalysis.crawler import (
    DATA_DIR, save_week, load_progress, save_progress, get_pending_weeks
)

SAMPLE_WEEK_DATA = {
    "number": 1,
    "config": {"subject": "测试", "name": "每周必看 01"},
    "videos": [{"aid": 123, "title": "测试视频"}]
}


class TestSaveWeek:
    @pytest.mark.asyncio
    async def test_saves_json_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        await save_week(1, SAMPLE_WEEK_DATA)

        filepath = tmp_path / "week_001.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["number"] == 1
        assert data["videos"][0]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_creates_directory_if_missing(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "raw"
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", data_dir)
        await save_week(5, SAMPLE_WEEK_DATA)

        assert (data_dir / "week_005.json").exists()

    @pytest.mark.asyncio
    async def test_pads_number_to_three_digits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        await save_week(42, SAMPLE_WEEK_DATA)

        assert (tmp_path / "week_042.json").exists()
        assert not (tmp_path / "week_42.json").exists()


class TestProgress:
    def test_load_progress_returns_default_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        progress = load_progress()
        assert progress == {"crawled": [], "failed": {}, "last_run": None}

    def test_save_and_load_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        state = {
            "crawled": [1, 2, 3],
            "failed": {"15": "timeout"},
            "last_run": "2026-06-15T10:30:00"
        }
        save_progress(state)
        loaded = load_progress()
        assert loaded["crawled"] == [1, 2, 3]
        assert loaded["failed"] == {"15": "timeout"}


class TestGetPendingWeeks:
    def test_all_pending_when_no_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        retry, pending = get_pending_weeks(5)
        assert pending == [1, 2, 3, 4, 5]
        assert retry == []

    def test_excludes_crawled(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [1, 2], "failed": {}, "last_run": None})
        retry, pending = get_pending_weeks(5)
        assert pending == [3, 4, 5]
        assert retry == []

    def test_returns_failed_as_retry(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [1, 2], "failed": {"3": "timeout"}, "last_run": None})
        retry, pending = get_pending_weeks(5)
        assert pending == [4, 5]
        assert retry == [3]

    def test_excludes_beyond_latest(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        retry, pending = get_pending_weeks(3)
        assert pending == [1, 2, 3]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_storage.py -v`
Expected: FAIL — module not found

#### Step 3: Write storage.py

Create `src/crawler/storage.py`:

```python
"""数据存取与进度管理。"""
import json
import asyncio
from pathlib import Path

DATA_DIR = Path("data/raw")


async def save_week(number: int, data: dict) -> None:
    """保存单期 JSON 文件到 data/raw/week_{number:03d}.json。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"week_{number:03d}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    await asyncio.to_thread(filepath.write_text, content, encoding="utf-8")


def _progress_path() -> Path:
    return DATA_DIR / "progress.json"


def load_progress() -> dict:
    """读取 progress.json，文件不存在时返回默认空结构。"""
    path = _progress_path()
    if not path.exists():
        return {"crawled": [], "failed": {}, "last_run": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(state: dict) -> None:
    """写入 progress.json。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, ensure_ascii=False, indent=2)
    _progress_path().write_text(content, encoding="utf-8")


def get_pending_weeks(latest_number: int) -> tuple[list[int], list[int]]:
    """对比 progress.json，返回 (retry, pending)。
       retry: 历史失败的期号列表，每次 run 重新尝试一次
       pending: 从未爬取的新期号列表"""
    progress = load_progress()
    crawled = set(progress.get("crawled", []))
    failed = set(int(k) for k in progress.get("failed", {}).keys())
    all_weeks = set(range(1, latest_number + 1))
    done = crawled - failed  # 成功爬取的
    retry = sorted(failed)
    pending = sorted(all_weeks - done - failed)
    return retry, pending
```

- [ ] **Step 4: Run storage tests**

Run: `uv run pytest tests/test_storage.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/crawler/storage.py tests/test_storage.py
git commit -m "feat: add weekly data storage and progress tracking"
```

---

### Task 5: 创建 pipeline.py

**Files:**
- Create: `src/crawler/pipeline.py`
- Create: `tests/test_pipeline.py`

#### Step 1: Write tests for pipeline.py

Create `tests/test_pipeline.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bilianalysis.crawler import CrawlConfig, CrawlReport, run
from bilianalysis.utils.fetch import HttpError

SERIES_LIST = [
    {"number": 1, "subject": "第一期"},
    {"number": 2, "subject": "第二期"},
    {"number": 3, "subject": "第三期"},
]

WEEKLY_DATA = {
    "config": {"number": 1, "subject": "第一期"},
    "list": [{"aid": 123, "title": "test"}]
}


class TestCrawlConfig:
    def test_defaults(self):
        config = CrawlConfig()
        assert config.mode == "sequential"
        assert config.concurrency == 3
        assert config.request_delay == 2.5
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_override(self):
        config = CrawlConfig(mode="concurrent", concurrency=5)
        assert config.mode == "concurrent"
        assert config.concurrency == 5


class TestCrawlReport:
    def test_create_report(self):
        report = CrawlReport(
            total=10,
            crawled=5,
            skipped=2,
            failed=3,
            failed_weeks={1: "timeout", 2: "404", 3: "500"},
            duration_seconds=12.5
        )
        assert report.total == 10
        assert report.failed == 3
        assert len(report.failed_weeks) == 3


class TestRun:
    @pytest.mark.asyncio
    async def test_full_crawl_success(self, tmp_path, monkeypatch):
        """集成测试：模拟完整爬取流程"""
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)

        # Mock api functions
        mock_list_series = AsyncMock(return_value=SERIES_LIST)
        mock_get_weekly = AsyncMock(return_value=WEEKLY_DATA)

        with patch("src.crawler.pipeline.list_series", mock_list_series):
            with patch("src.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                config = CrawlConfig(mode="sequential", request_delay=0, retry_delay=0)
                report = await run(config)

        assert report.total == 3
        assert report.crawled == 3
        assert report.skipped == 0
        assert report.failed == 0
        assert report.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_skips_already_crawled(self, tmp_path, monkeypatch):
        """已爬取的期号被跳过"""
        from bilianalysis.crawler import save_progress
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [1, 2], "failed": {}, "last_run": None})

        mock_list_series = AsyncMock(return_value=SERIES_LIST)
        mock_get_weekly = AsyncMock(return_value=WEEKLY_DATA)

        with patch("src.crawler.pipeline.list_series", mock_list_series):
            with patch("src.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                config = CrawlConfig(mode="sequential", request_delay=0, retry_delay=0)
                report = await run(config)

        assert report.skipped == 2
        assert report.crawled == 1  # only week 3
        assert mock_get_weekly.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_failed_then_skips(self, tmp_path, monkeypatch):
        """失败期号重试一次，仍失败则保留"""
        from bilianalysis.crawler import save_progress, load_progress
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [1], "failed": {"2": "prev timeout"}, "last_run": None})

        # week 2 still fails, week 3 succeeds
        call_count = 0

        async def mock_get_weekly(session, number):
            nonlocal call_count
            call_count += 1
            if number == 2:
                raise HttpError(502, "bad gateway")
            return WEEKLY_DATA

        with patch("src.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
            with patch("src.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                config = CrawlConfig(mode="sequential", request_delay=0, retry_delay=0)
                report = await run(config)

        assert report.crawled == 1  # only week 3
        assert report.skipped == 1  # week 1 already done
        assert report.failed == 1  # week 2 failed again
        assert 2 in report.failed_weeks

        progress = load_progress()
        assert "2" in progress["failed"]  # still in failed
        assert 3 in progress["crawled"]

    @pytest.mark.asyncio
    async def test_failed_retry_recovered(self, tmp_path, monkeypatch):
        """失败期号重试成功，从 failed 移除"""
        from bilianalysis.crawler import save_progress, load_progress
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [1], "failed": {"2": "prev timeout"}, "last_run": None})

        # week 2 now succeeds
        async def mock_get_weekly(session, number):
            return WEEKLY_DATA

        with patch("src.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
            with patch("src.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                config = CrawlConfig(mode="sequential", request_delay=0, retry_delay=0)
                report = await run(config)

        progress = load_progress()
        assert "2" not in progress["failed"]
        assert 2 in progress["crawled"]

    @pytest.mark.asyncio
    async def test_concurrent_mode(self, tmp_path, monkeypatch):
        """并发模式正常完成"""
        from bilianalysis.crawler import save_progress
        monkeypatch.setattr("src.crawler.storage.DATA_DIR", tmp_path)
        save_progress({"crawled": [], "failed": {}, "last_run": None})

        with patch("src.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
            with patch("src.crawler.pipeline.get_weekly_videos", AsyncMock(return_value=WEEKLY_DATA)):
                config = CrawlConfig(mode="concurrent", concurrency=3, retry_delay=0)
                report = await run(config)

        assert report.crawled == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — module not found

#### Step 3: Write pipeline.py

Create `src/crawler/pipeline.py`:

```python
"""爬取编排：速率控制、重试、续爬、并发模式。"""
import asyncio
import time
from typing import Literal
from pydantic import BaseModel
import aiohttp

from bilianalysis.crawler import list_series, get_weekly_videos
from bilianalysis.crawler import save_week, load_progress, save_progress, get_pending_weeks
from bilianalysis.utils.fetch import create_session, HttpError


class CrawlConfig(BaseModel):
    mode: Literal["sequential", "concurrent"] = "sequential"
    concurrency: int = 3
    request_delay: float = 2.5
    max_retries: int = 3
    retry_delay: float = 1.0


class CrawlReport(BaseModel):
    total: int
    crawled: int
    skipped: int
    failed: int
    failed_weeks: dict[int, str]
    duration_seconds: float


async def run(config: CrawlConfig = CrawlConfig()) -> CrawlReport:
    """执行一次完整爬取。供外部模块调用。"""
    start_time = time.monotonic()
    crawled_count = 0
    failed_count = 0
    failed_details: dict[int, str] = {}

    session = create_session()
    try:
        # 1. 获取所有期号
        series = await list_series(session)
        if not series:
            return CrawlReport(
                total=0, crawled=0, skipped=0, failed=0,
                failed_weeks={}, duration_seconds=time.monotonic() - start_time
            )
        latest = max(s["number"] for s in series)
        total = latest

        # 2. 获取待爬列表
        retry_list, pending_list = get_pending_weeks(latest)

        # 计算已跳过数（之前已成功爬取的）
        progress = load_progress()
        already_crawled = set(progress.get("crawled", []))
        failed_set = set(int(k) for k in progress.get("failed", {}).keys())
        already_done = already_crawled - failed_set
        skipped_count = len(already_done)

        # 3. 先处理历史失败期号（每个仅尝试 1 次）
        for number in retry_list:
            try:
                data = await get_weekly_videos(session, number)
            except HttpError as e:
                progress["failed"][str(number)] = str(e)
                failed_count += 1
                failed_details[number] = str(e)
                continue
            await save_week(number, {"number": number, "config": data.get("config", {}),
                                     "videos": data.get("list", [])})
            progress["failed"].pop(str(number), None)
            if number not in progress["crawled"]:
                progress["crawled"].append(number)
            crawled_count += 1
        save_progress(progress)

        # 4. 处理新期号
        if config.mode == "sequential":
            for number in pending_list:
                success, err_msg = await _crawl_one(session, number, config)
                if success:
                    crawled_count += 1
                else:
                    failed_count += 1
                    failed_details[number] = err_msg
                await asyncio.sleep(config.request_delay)
        else:
            semaphore = asyncio.Semaphore(config.concurrency)

            async def crawl_with_semaphore(number):
                async with semaphore:
                    success, err_msg = await _crawl_one(session, number, config)
                    return number, success, err_msg

            results = await asyncio.gather(
                *(crawl_with_semaphore(n) for n in pending_list)
            )
            for number, success, err_msg in results:
                if success:
                    crawled_count += 1
                else:
                    failed_count += 1
                    failed_details[number] = err_msg

        # 5. 更新最后运行时间
        progress = load_progress()
        progress["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save_progress(progress)

        duration = time.monotonic() - start_time
        return CrawlReport(
            total=total,
            crawled=crawled_count,
            skipped=skipped_count,
            failed=failed_count,
            failed_weeks=failed_details,
            duration_seconds=round(duration, 2)
        )
    finally:
        await session.close()


async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlConfig) -> tuple[bool, str]:
    """爬取单期，含重试逻辑。返回 (成功, 错误信息)。"""
    last_error = ""
    for attempt in range(1, config.max_retries + 1):
        try:
            data = await get_weekly_videos(session, number)
        except HttpError as e:
            last_error = str(e)
            if attempt < config.max_retries:
                await asyncio.sleep(config.retry_delay)
            continue

        # 成功
        await save_week(number, {"number": number, "config": data.get("config", {}),
                                 "videos": data.get("list", [])})
        progress = load_progress()
        if number not in progress["crawled"]:
            progress["crawled"].append(number)
        progress["failed"].pop(str(number), None)
        save_progress(progress)
        return True, ""

    # 全部重试失败
    progress = load_progress()
    progress["failed"][str(number)] = last_error
    save_progress(progress)
    return False, last_error
```

- [ ] **Step 4: Run pipeline tests**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/crawler/pipeline.py tests/test_pipeline.py
git commit -m "feat: add crawler pipeline with retry, resume, and concurrent modes"
```

---

### Task 6: 最终验证

- [ ] **Step 1: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (11 + 5 + 9 + 8 = 33)

- [ ] **Step 2: Run import smoke test**

Run: `uv run python -c "from src.crawler.pipeline import run, CrawlConfig, CrawlReport; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify main.py untouched**

Run: `git diff main.py`
Expected: no diff (or confirm main.py unchanged)

- [ ] **Step 4: Final commit if needed**

```bash
git add .
git commit -m "chore: final verification, all crawler tests passing"
```
