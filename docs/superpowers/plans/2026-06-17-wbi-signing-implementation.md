# WBI 签名 API 策略实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Bilibili API 请求添加 WBI 签名参数（web_location, w_rid, wts），替换裸 GET 请求。

**Architecture:** 新增 `signer.py`（fetch_mixin_key + WbiSigner）→ 修改 `api.py` 两个端点接受 signer → 修改 `pipeline.py` 在 run() 启动时获取 mixin_key 并下传。

**Tech Stack:** hashlib, urllib.parse, time（均为标准库，无新依赖）

---

### Task 1: Create signer.py

**Files:**
- Create: `src/bilianalysis/crawler/signer.py`

- [ ] **Step 1: Create signer.py**

Create `src/bilianalysis/crawler/signer.py`:

```python
"""WBI 签名模块：fetch_mixin_key + WbiSigner。"""
import hashlib
import time
from typing import Any
from urllib.parse import urlencode

import aiohttp
from bilianalysis.utils.fetch import get

MIXIN_TABLE = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
               27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
               37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
               22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44, 34]

WEB_LOCATION = "333.934"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"


async def fetch_mixin_key(session: aiohttp.ClientSession) -> str:
    """从 nav 接口获取 img_key + sub_key，计算 mixin_key。"""
    resp = await get(session, NAV_URL)
    wbi_img: dict[str, str] = resp.get("data", {}).get("wbi_img", {})
    img_url: str = wbi_img.get("img_url", "")
    sub_url: str = wbi_img.get("sub_url", "")

    # 从 URL 提取文件名，去掉路径和 .png 后缀
    img_key = img_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    sub_key = sub_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    raw = img_key + sub_key
    mixin = "".join(raw[i] for i in MIXIN_TABLE[:32])
    return mixin


class WbiSigner:
    """WBI 签名器。持有 mixin_key，提供 sign(params) 方法。"""

    def __init__(self, mixin_key: str):
        self._key = mixin_key

    def sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """对参数追加 wts + web_location + w_rid 后返回完整参数字典。"""
        signed: dict[str, Any] = dict(params)
        signed["wts"] = str(int(time.time()))
        signed["web_location"] = WEB_LOCATION
        signed["w_rid"] = self._compute_wrid(signed)
        return signed

    def _compute_wrid(self, params: dict[str, Any]) -> str:
        sorted_items = sorted(params.items(), key=lambda x: x[0])
        qs = urlencode(sorted_items)
        return hashlib.md5((qs + self._key).encode()).hexdigest()
```

- [ ] **Step 2: Verify import**

Run: `uv run python -c "from bilianalysis.crawler.signer import fetch_mixin_key, WbiSigner; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/crawler/signer.py
git commit -m "feat: add WBI signer module (fetch_mixin_key + WbiSigner)"
```

---

### Task 2: Create tests for signer.py

**Files:**
- Create: `tests/test_signer.py`

- [ ] **Step 1: Write test_signer.py**

Create `tests/test_signer.py`:

```python
"""测试 WBI 签名模块。"""
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from bilianalysis.crawler.signer import (
    fetch_mixin_key, WbiSigner, WEB_LOCATION, MIXIN_TABLE, NAV_URL,
)


NAV_RESPONSE = {
    "code": 0,
    "data": {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/abc123def.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/ghi456jkl.png",
        }
    }
}


class TestFetchMixinKey:
    @pytest.mark.asyncio
    async def test_returns_mixin_key_from_valid_response(self):
        mock_get = AsyncMock(return_value=NAV_RESPONSE)
        with patch("bilianalysis.crawler.signer.get", mock_get):
            result = await fetch_mixin_key(MagicMock())

        assert isinstance(result, str)
        assert len(result) == 32
        # Verify it uses the right URL
        call_args = mock_get.call_args[0]
        assert call_args[1] == NAV_URL

    @pytest.mark.asyncio
    async def test_mixin_key_derivation(self):
        """手动验证 mixin_key 推导逻辑。"""
        resp = {"data": {"wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b840f84.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
        }}}
        mock_get = AsyncMock(return_value=resp)
        with patch("bilianalysis.crawler.signer.get", mock_get):
            result = await fetch_mixin_key(MagicMock())

        # Manual computation
        img_key = "7cd084941338484aae1ad9425b840f84"
        sub_key = "4932caff0ff746eab6f01bf08b70ac45"
        raw = img_key + sub_key
        expected = "".join(raw[i] for i in MIXIN_TABLE[:32])
        assert result == expected


class TestWbiSigner:
    def test_sign_adds_required_params(self):
        signer = WbiSigner("a" * 32)
        result = signer.sign({})
        assert "wts" in result
        assert "web_location" in result
        assert "w_rid" in result
        assert result["web_location"] == WEB_LOCATION
        assert len(result["w_rid"]) == 32  # MD5 hex

    def test_sign_preserves_input_params(self):
        signer = WbiSigner("b" * 32)
        result = signer.sign({"number": "123"})
        assert result.get("number") == "123"

    def test_sign_deterministic_with_fixed_time(self, monkeypatch):
        """固定时间戳时，签名是确定性的。"""
        import bilianalysis.crawler.signer as mod
        monkeypatch.setattr(mod.time, "time", lambda: 1781522463)
        signer = WbiSigner("test_key_32_bytes_123456789")
        result = signer.sign({"number": "377"})

        assert result["wts"] == "1781522463"
        # 手动计算预期 w_rid
        # sorted: number=377, web_location=333.934, wts=1781522463
        qs = "number=377&web_location=333.934&wts=1781522463"
        expected_wrid = hashlib.md5((qs + "test_key_32_bytes_123456789").encode()).hexdigest()
        assert result["w_rid"] == expected_wrid

    def test_sign_params_alphabetically_ordered(self, monkeypatch):
        """验证参数按 key 字母序排列。"""
        import bilianalysis.crawler.signer as mod
        monkeypatch.setattr(mod.time, "time", lambda: 1781522463)
        signer = WbiSigner("x" * 32)

        # 传入非字母序的参数，内部应重新排序
        result = signer.sign({"z_param": "1", "a_param": "2"})
        # w_rid 的计算应该基于排序后的 query string
        qs = "a_param=2&web_location=333.934&wts=1781522463&z_param=1"
        expected = hashlib.md5((qs + "x" * 32).encode()).hexdigest()
        assert result["w_rid"] == expected
```

- [ ] **Step 2: Run signer tests**

Run: `uv run pytest tests/test_signer.py -v`
Expected: 6 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_signer.py
git commit -m "test: add WBI signer unit tests (6 tests)"
```

---

### Task 3: Modify api.py

**Files:**
- Modify: `src/bilianalysis/crawler/api.py`

- [ ] **Step 1: Verify existing tests pass first**

Run: `uv run pytest tests/test_api.py -v`
Expected: 5 PASS (current state, will break after modification)

- [ ] **Step 2: Modify api.py**

Replace `src/bilianalysis/crawler/api.py` with:

```python
"""Bilibili "每周必看" API 封装。"""
from typing import Any
from urllib.parse import urlencode

import aiohttp
from bilianalysis.utils.fetch import get
from bilianalysis.crawler.signer import WbiSigner

BASE_URL = "https://api.bilibili.com/x/web-interface/popular/series"


async def list_series(
    session: aiohttp.ClientSession, signer: WbiSigner
) -> list[dict[str, Any]]:
    """获取所有期数列表。返回 data.list，按 number 升序排列。"""
    params = signer.sign({})
    url = f"{BASE_URL}/list?{urlencode(params)}"
    resp = await get(session, url)
    items: list[dict[str, Any]] = resp.get("data", {}).get("list", [])
    items.sort(key=lambda x: x.get("number", 0))
    return items


async def get_weekly_videos(
    session: aiohttp.ClientSession, number: int, signer: WbiSigner
) -> dict[str, Any]:
    """获取指定期数的完整数据。返回 API 原始 data 字典 {config, list}。
       HttpError 直接透传，由 pipeline 层捕获处理。"""
    params = signer.sign({"number": str(number)})
    url = f"{BASE_URL}/one?{urlencode(params)}"
    resp = await get(session, url)
    return resp.get("data", {})
```

- [ ] **Step 3: Verify api.py tests now fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `list_series()` and `get_weekly_videos()` now require `signer` argument

---

### Task 4: Update test_api.py

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: Update test_api.py**

Replace the entire `tests/test_api.py` with:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bilianalysis.crawler import list_series, get_weekly_videos, BASE_URL
from bilianalysis.crawler.signer import WbiSigner
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


@pytest.fixture
def signer():
    """创建一个测试用 WbiSigner（固定 mixin_key）。"""
    return WbiSigner("test_key_32_bytes_0123456789")


class TestListSeries:
    @pytest.mark.asyncio
    async def test_returns_series_list(self, signer):
        with patch("bilianalysis.crawler.api.get", AsyncMock(return_value=SERIES_LIST_RESPONSE)):
            result = await list_series(MagicMock(), signer)
        assert len(result) == 3
        assert result[0]["number"] == 1
        assert result[-1]["number"] == 3

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, signer):
        mock_get = AsyncMock(return_value=SERIES_LIST_RESPONSE)
        with patch("bilianalysis.crawler.api.get", mock_get):
            await list_series(MagicMock(), signer)
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0]
        url = call_args[1]
        assert url.startswith(f"{BASE_URL}/list?")
        assert "web_location=333.934" in url
        assert "w_rid=" in url
        assert "wts=" in url


class TestGetWeeklyVideos:
    @pytest.mark.asyncio
    async def test_returns_data_dict(self, signer):
        with patch("bilianalysis.crawler.api.get", AsyncMock(return_value=SERIES_ONE_RESPONSE)):
            result = await get_weekly_videos(MagicMock(), 1, signer)
        assert result["config"]["number"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_url_includes_number(self, signer):
        mock_get = AsyncMock(return_value=SERIES_ONE_RESPONSE)
        with patch("bilianalysis.crawler.api.get", mock_get):
            await get_weekly_videos(MagicMock(), 42, signer)
        call_args = mock_get.call_args[0]
        url = call_args[1]
        assert "number=42" in url
        assert url.startswith(f"{BASE_URL}/one?")

    @pytest.mark.asyncio
    async def test_propagates_http_error(self, signer):
        err = HttpError(502, "bad gateway")
        mock_get = AsyncMock(side_effect=err)
        with patch("bilianalysis.crawler.api.get", mock_get):
            with pytest.raises(HttpError) as exc_info:
                await get_weekly_videos(MagicMock(), 1, signer)
            assert exc_info.value.status == 502
```

- [ ] **Step 2: Run api tests**

Run: `uv run pytest tests/test_api.py -v`
Expected: 5 PASS (all tests adapted to new signer parameter)

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/crawler/api.py tests/test_api.py
git commit -m "feat: add WBI signer parameter to api endpoints"
```

---

### Task 5: Modify pipeline.py

**Files:**
- Modify: `src/bilianalysis/crawler/pipeline.py`

- [ ] **Step 1: Read current pipeline.py and apply edits**

Modify `src/bilianalysis/crawler/pipeline.py`:

**Edit 1**: Add import after existing imports (after line 14 `from bilianalysis.utils.fetch import create_session, HttpError`):

```python
from .signer import fetch_mixin_key, WbiSigner
```

**Edit 2**: In `run()`, after `session = create_session()` (line 39), before `try:` block, add:

```python
    session = create_session()
    mixin_key = await fetch_mixin_key(session)
    signer = WbiSigner(mixin_key)
    try:
```

**Edit 3**: Change `list_series(session)` call:

```python
# line ~42: change this:
        series = await list_series(session)
# to:
        series = await list_series(session, signer)
```

**Edit 4**: Change retry phase `get_weekly_videos` call:

```python
# line ~64: change this:
                data = await get_weekly_videos(session, number)
# to:
                data = await get_weekly_videos(session, number, signer)
```

**Edit 5**: Change `_crawl_one` function signature:

```python
# line ~124: change this:
async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection) -> tuple[bool, str]:
# to:
async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection, signer: WbiSigner) -> tuple[bool, str]:
```

**Edit 6**: In `_crawl_one`, change `get_weekly_videos` call:

```python
# line ~130: change this:
            data = await get_weekly_videos(session, number)
# to:
            data = await get_weekly_videos(session, number, signer)
```

**Edit 7**: In the sequential mode, change `_crawl_one` call:

```python
# line ~81: change this:
                success, err_msg = await _crawl_one(session, number, config)
# to:
                success, err_msg = await _crawl_one(session, number, config, signer)
```

**Edit 8**: In concurrent mode `crawl_with_semaphore`, change `_crawl_one` call:

```python
# line ~93: change this:
                    success, err_msg = await _crawl_one(session, number, config)
# to:
                    success, err_msg = await _crawl_one(session, number, config, signer)
```

- [ ] **Step 2: Run pipeline tests to see what breaks**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — tests mock `list_series` and `get_weekly_videos` but pipeline now passes `signer`

---

### Task 6: Update test_pipeline.py

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Update test_pipeline.py**

**Edit 1**: Add import (after line 6):

```python
from bilianalysis.crawler.signer import WbiSigner
```

**Edit 2**: Add fixture at top of `TestRun` class (before first test method):

```python
class TestRun:
    @pytest.fixture
    def signer(self):
        return WbiSigner("test_key_32_bytes_0123456789")
```

**Edit 3**: Add `fetch_mixin_key` mock to each test method. For every `TestRun` test method, add a `patch` for `fetch_mixin_key`. Example for `test_full_crawl_success`:

```python
    @pytest.mark.asyncio
    async def test_full_crawl_success(self, tmp_path, monkeypatch, signer):
        """集成测试：模拟完整爬取流程"""
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)

        mock_list_series = AsyncMock(return_value=SERIES_LIST)
        mock_get_weekly = AsyncMock(return_value=WEEKLY_DATA)
        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", mock_list_series):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                    config = CrawlerSection(mode="sequential", request_delay=0, retry_delay=0)
                    report = await run(config)

        assert report.total == 3
        ...
```

Apply the same `with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):` wrapper to ALL five `TestRun` test methods: `test_full_crawl_success`, `test_skips_already_crawled`, `test_retries_failed_then_skips`, `test_failed_retry_recovered`, `test_concurrent_mode`.

**Edit 4**: Update `test_retries_failed_then_skips` mock signature — the inline `mock_get_weekly` function signature needs to accept `signer`:

```python
        async def mock_get_weekly(session, number, signer=None):
            if number == 2:
                raise HttpError(502, "bad gateway")
            return WEEKLY_DATA
```

**Edit 5**: Update `test_failed_retry_recovered` mock signature:

```python
        async def mock_get_weekly(session, number, signer=None):
            return WEEKLY_DATA
```

- [ ] **Step 2: Run pipeline tests**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: 8 PASS

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/crawler/pipeline.py tests/test_pipeline.py
git commit -m "feat: integrate WBI signer into crawl pipeline"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (~73 existing + ~6 new signer tests = ~79 total)

- [ ] **Step 2: Verify crawler public API**

Run: `uv run python -c "from bilianalysis.crawler import CrawlRunner, CrawlReport, WbiSigner; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: final verification for WBI signing feature" --allow-empty
```
