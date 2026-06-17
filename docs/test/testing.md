# 测试文档

## 一、概述

测试框架：`pytest` + `pytest-asyncio`，`asyncio_mode = "auto"`（无需手动给 async 测试加装饰器）。

```
tests/
├── test_fetch.py      # 14 tests — HttpError, create_session, get, post
├── test_api.py        #  5 tests — list_series, get_weekly_videos
├── test_storage.py    #  9 tests — save_week, progress 管理, get_pending_weeks
└── test_pipeline.py   #  8 tests — CrawlConfig, CrawlReport, run (集成)
                       # ─────────────────
                       # 36 tests total
```

## 二、运行命令

```bash
# 全部测试
uv run pytest tests/ -v

# 单个文件
uv run pytest tests/test_storage.py -v

# 单个测试类
uv run pytest tests/test_storage.py::TestGetPendingWeeks -v

# 单个测试
uv run pytest tests/test_pipeline.py::TestRun::test_concurrent_mode -v

# 匹配名称
uv run pytest tests/ -k "failed" -v
```

## 三、Mock 策略

### 3.1 测试层级隔离

| 测试文件 | Mock 目标 | 原因 |
|----------|----------|------|
| `test_fetch.py` | 直接 mock `aiohttp.ClientSession` | fetch 是最底层，测试 HTTP 行为 |
| `test_api.py` | `patch("bilianalysis.crawler.api.get")` | 隔离 fetch，只测 URL 构造和数据提取 |
| `test_storage.py` | 用 `tmp_path` 重定向 `DATA_DIR` | 文件 IO 用真实操作，不走 mock |
| `test_pipeline.py` | `patch("bilianalysis.crawler.pipeline.list_series")` 和 `get_weekly_videos` | 隔离 API 层，测试编排逻辑 |

### 3.2 Patch 路径规则

Mock `unittest.mock.patch` 必须 patch **目标模块导入该符号的命名空间**：

```python
# api.py 中: from bilianalysis.utils.fetch import get
# 正确 — patch api.py 中的引用
with patch("bilianalysis.crawler.api.get", mock_obj):
    ...

# pipeline.py 中: from bilianalysis.crawler.api import list_series
# 正确 — patch pipeline.py 中的引用
with patch("bilianalysis.crawler.pipeline.list_series", mock_obj):
    ...

# 错误 — patch 定义位置不会生效
with patch("bilianalysis.crawler.api.list_series", mock_obj):  # pipeline 里用的是自己的引用
    ...
```

### 3.3 AsyncMock 模式

测试 async 函数的标准模式：

```python
mock_obj = AsyncMock(return_value=expected_data)

with patch("target.module.function", mock_obj):
    result = await function_under_test()

mock_obj.assert_called_once()
call_args = mock_obj.call_args[0]  # 位置参数
call_kwargs = mock_obj.call_args[1]  # 关键字参数（需要 mock 使用了 kwargs）
```

模拟 async context manager（`async with`）：

```python
mock_resp = AsyncMock()
mock_resp.status = 200
mock_resp.content_type = "application/json"
mock_resp.json = AsyncMock(return_value={"data": "value"})
mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)  # async with 进入
mock_resp.__aexit__ = AsyncMock(return_value=None)         # async with 退出
```

模拟异常：

```python
mock_obj = AsyncMock(side_effect=HttpError(502, "bad gateway"))
```

## 四、Fixture 使用

### tmp_path

`test_storage.py` 和 `test_pipeline.py` 使用 `tmp_path` 避免污染真实文件系统：

```python
monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
```

每次测试独立一个临时目录，测试结束自动清理。

### Module-level 测试常量

```python
SERIES_LIST = [
    {"number": 1, "subject": "第一期"},
    {"number": 2, "subject": "第二期"},
    {"number": 3, "subject": "第三期"},
]

WEEKLY_DATA = {
    "config": {"number": 1, "subject": "第一期"},
    "list": [{"aid": 123, "title": "test"}]
}
```

多个测试类共享，避免在类中重复定义。

## 五、测试覆盖矩阵

### test_fetch.py (14 tests)

| 测试 | 覆盖 |
|------|------|
| `TestHttpError::test_http_error_has_status_and_message` | status/message 属性 + `__str__` |
| `TestHttpError::test_http_error_default_message` | 无 message 时的默认值 |
| `TestCreateSession::test_returns_client_session` | 返回 aiohttp Session |
| `TestCreateSession::test_uses_default_timeout` | 默认超时配置 |
| `TestCreateSession::test_custom_timeout` | 自定义超时 |
| `TestGet::test_get_json_success` | 200 + JSON content-type |
| `TestGet::test_get_text_response` | 200 + HTML content-type |
| `TestGet::test_get_non_200_raises_http_error` | 404 → HttpError |
| `TestGet::test_get_passes_headers_to_session` | 自定义 headers 传递 |
| `TestGet::test_get_network_error_raises_http_error` | ClientError → HttpError(0) |
| `TestPost::test_post_json_success` | JSON POST |
| `TestPost::test_post_with_data_param` | form-encoded POST |
| `TestPost::test_post_text_response` | 非 JSON POST 响应 |
| `TestPost::test_post_non_200_raises_http_error` | 500 → HttpError |

### test_api.py (5 tests)

| 测试 | 覆盖 |
|------|------|
| `TestListSeries::test_returns_series_list` | 返回排序后的列表 |
| `TestListSeries::test_calls_correct_url` | URL 拼接正确 |
| `TestGetWeeklyVideos::test_returns_data_dict` | 返回 data 字段 |
| `TestGetWeeklyVideos::test_url_includes_number` | number 参数拼入 URL |
| `TestGetWeeklyVideos::test_propagates_http_error` | HttpError 透传 |

### test_storage.py (9 tests)

| 测试 | 覆盖 |
|------|------|
| `TestSaveWeek::test_saves_json_file` | 保存 JSON、内容正确 |
| `TestSaveWeek::test_creates_directory_if_missing` | 自动创建目录 |
| `TestSaveWeek::test_pads_number_to_three_digits` | 文件名 3 位补零 |
| `TestProgress::test_load_progress_returns_default_when_no_file` | 无文件返回默认值 |
| `TestProgress::test_save_and_load_progress` | 写入+读取往返 |
| `TestGetPendingWeeks::test_all_pending_when_no_progress` | 全量待爬 |
| `TestGetPendingWeeks::test_excludes_crawled` | 排除已爬取 |
| `TestGetPendingWeeks::test_returns_failed_as_retry` | 失败期号出现在 retry 列表 |
| `TestGetPendingWeeks::test_excludes_beyond_latest` | 不包含超出最新期号的范围 |

### test_pipeline.py (8 tests)

| 测试 | 覆盖 |
|------|------|
| `TestCrawlConfig::test_defaults` | 默认配置值 |
| `TestCrawlConfig::test_override` | 配置覆盖 |
| `TestCrawlReport::test_create_report` | 报告模型创建 |
| `TestRun::test_full_crawl_success` | 完整串行爬取成功 |
| `TestRun::test_skips_already_crawled` | 已爬期号跳过 |
| `TestRun::test_retries_failed_then_skips` | 失败重试+仍失败保留 |
| `TestRun::test_failed_retry_recovered` | 失败重试+恢复 |
| `TestRun::test_concurrent_mode` | 并发模式正确完成 |

## 六、编写新测试

### 测试 async 函数

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_async_function():
    with patch("target.module.dependency", AsyncMock(return_value=expected)):
        result = await my_function()
    assert result == expected
```

### 测试文件 I/O

```python
@pytest.mark.asyncio
async def test_file_io(self, tmp_path, monkeypatch):
    monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
    # 测试代码
```

### 测试 Pydantic 模型

```python
def test_model():
    config = CrawlConfig(mode="concurrent")
    assert config.mode == "concurrent"
    assert config.concurrency == 3  # 默认值
```

## 七、CI 运行

```bash
# 本地运行（等同于 CI）
uv sync
uv run pytest tests/ -v
```

期望：36 passed，0 failed。任何 PR 应确保全部通过。
