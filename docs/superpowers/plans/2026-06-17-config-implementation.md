# 配置功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现全项目统一配置系统 — YAML 文件 + 环境变量覆盖，覆盖 crawler/analysis/data 三个模块。

**Architecture:** 三层结构 — `model.py`（纯 Pydantic 数据模型）→ `loader.py`（YAML 读取 + env 合并）→ `__init__.py`（公开 API）。pipeline.py 删除 `CrawlConfig`，改用 `CrawlerSection`。

**Tech Stack:** pydantic-settings, pyyaml, Pydantic BaseModel

---

## 文件结构

```
新建: src/bilianalysis/config/__init__.py     # 公开 API
新建: src/bilianalysis/config/model.py       # AppConfig + 3 个子节模型
新建: src/bilianalysis/config/loader.py      # load_config() 

新建: tests/test_config.py                   # config 模块测试

修改: src/bilianalysis/crawler/pipeline.py   # 删除 CrawlConfig → 引入 CrawlerSection
修改: src/bilianalysis/crawler/__init__.py   # 更新导出
修改: tests/test_pipeline.py                 # CrawlConfig → CrawlerSection
```

---

### Task 1: 添加依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Install pydantic-settings and pyyaml**

Run: `uv add pydantic-settings pyyaml`

- [ ] **Step 2: Verify imports**

Run: `uv run python -c "from pydantic_settings import BaseSettings; import yaml; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pydantic-settings and pyyaml"
```

---

### Task 2: 创建 model.py

**Files:**
- Create: `src/bilianalysis/config/__init__.py` (empty placeholder)
- Create: `src/bilianalysis/config/model.py`

#### Step 1: Write tests

Create `tests/test_config.py`:

```python
import pytest
from bilianalysis.config.model import (
    CrawlerSection, AnalysisSection, DataSection, AppConfig
)


class TestCrawlerSection:
    def test_defaults(self):
        cfg = CrawlerSection()
        assert cfg.mode == "sequential"
        assert cfg.concurrency == 3
        assert cfg.request_delay == 2.5
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 1.0

    def test_override_fields(self):
        cfg = CrawlerSection(mode="concurrent", concurrency=5)
        assert cfg.mode == "concurrent"
        assert cfg.concurrency == 5
        # unset fields use defaults
        assert cfg.request_delay == 2.5


class TestAnalysisSection:
    def test_defaults(self):
        cfg = AnalysisSection()
        assert cfg.engine == "pandas"

    def test_override(self):
        cfg = AnalysisSection(engine="spark")
        assert cfg.engine == "spark"


class TestDataSection:
    def test_defaults(self):
        cfg = DataSection()
        assert cfg.raw_dir == "data/raw"
        assert cfg.processed_dir == "data/processed"
        assert cfg.reports_dir == "data/reports"


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.crawler.mode == "sequential"
        assert cfg.analysis.engine == "pandas"
        assert cfg.data.raw_dir == "data/raw"

    def test_nested_override(self):
        cfg = AppConfig(
            crawler=CrawlerSection(mode="concurrent"),
            analysis=AnalysisSection(engine="spark"),
        )
        assert cfg.crawler.mode == "concurrent"
        assert cfg.analysis.engine == "spark"
        # data section untouched
        assert cfg.data.processed_dir == "data/processed"
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — module not found

#### Step 3: Write model.py

Create `src/bilianalysis/config/model.py`:

```python
"""配置数据模型。纯 Pydantic，无 I/O 依赖。"""
from pydantic import BaseModel
from typing import Literal


class CrawlerSection(BaseModel):
    """爬虫配置节"""
    mode: Literal["sequential", "concurrent"] = "sequential"
    concurrency: int = 3
    request_delay: float = 2.5
    max_retries: int = 3
    retry_delay: float = 1.0


class AnalysisSection(BaseModel):
    """分析引擎配置节"""
    engine: Literal["pandas", "spark"] = "pandas"


class DataSection(BaseModel):
    """数据路径配置节"""
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    reports_dir: str = "data/reports"


class AppConfig(BaseModel):
    """应用根配置"""
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
```

Also create `src/bilianalysis/config/__init__.py` (empty, will be populated in Task 4).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/config/__init__.py src/bilianalysis/config/model.py tests/test_config.py
git commit -m "feat: add config data models (AppConfig, CrawlerSection, etc.)"
```

---

### Task 3: 创建 loader.py

**Files:**
- Create: `src/bilianalysis/config/loader.py`
- Modify: `tests/test_config.py` (append loader tests)

#### Step 1: Write loader tests

Append to `tests/test_config.py`:

```python
import os
import yaml
from unittest.mock import patch
from bilianalysis.config.loader import load_config
from bilianalysis.config.model import AppConfig


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """config.yaml 不存在时返回全默认值"""
        monkeypatch.chdir(tmp_path)
        cfg = load_config("nonexistent.yaml")
        assert isinstance(cfg, AppConfig)
        assert cfg.crawler.mode == "sequential"
        assert cfg.analysis.engine == "pandas"

    def test_loads_from_yaml_file(self, tmp_path, monkeypatch):
        """从 YAML 文件加载配置"""
        monkeypatch.chdir(tmp_path)
        yaml_content = {
            "crawler": {"mode": "concurrent", "concurrency": 10},
            "analysis": {"engine": "spark"},
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(yaml_content), encoding="utf-8")

        cfg = load_config(str(config_path))
        assert cfg.crawler.mode == "concurrent"
        assert cfg.crawler.concurrency == 10
        assert cfg.crawler.request_delay == 2.5  # default preserved
        assert cfg.analysis.engine == "spark"

    def test_partial_yaml_preserves_defaults(self, tmp_path, monkeypatch):
        """YAML 只写部分字段，其余使用默认值"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("crawler:\n  mode: concurrent\n", encoding="utf-8")

        cfg = load_config(str(config_path))
        assert cfg.crawler.mode == "concurrent"
        assert cfg.crawler.max_retries == 3  # default

    def test_env_var_overrides_yaml(self, tmp_path, monkeypatch):
        """环境变量覆盖 YAML 文件设置"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BILI_CRAWLER__MODE", "sequential")

        config_path = tmp_path / "config.yaml"
        config_path.write_text("crawler:\n  mode: concurrent\n", encoding="utf-8")

        cfg = load_config(str(config_path))
        # env var overrides yaml
        assert cfg.crawler.mode == "sequential"

    def test_bili_config_path_env(self, tmp_path, monkeypatch):
        """BILI_CONFIG_PATH 指定配置文件路径"""
        monkeypatch.chdir(tmp_path)
        custom_path = tmp_path / "prod.yaml"
        custom_path.write_text("crawler:\n  concurrency: 7\n", encoding="utf-8")
        monkeypatch.setenv("BILI_CONFIG_PATH", str(custom_path))

        cfg = load_config()
        assert cfg.crawler.concurrency == 7

    def test_empty_yaml_file(self, tmp_path, monkeypatch):
        """空 YAML 文件等同于全部默认值"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("", encoding="utf-8")

        cfg = load_config(str(config_path))
        assert cfg.crawler.mode == "sequential"

    @pytest.mark.asyncio  # not async, but marked for consistency
    def test_numeric_env_var_casting(self, tmp_path, monkeypatch):
        """pydantic-settings 自动将 env 字符串转为 int/float"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BILI_CRAWLER__CONCURRENCY", "20")
        monkeypatch.setenv("BILI_CRAWLER__REQUEST_DELAY", "5.0")

        cfg = load_config("nonexistent.yaml")
        assert cfg.crawler.concurrency == 20
        assert cfg.crawler.request_delay == 5.0

    def test_parameter_overrides_env(self, tmp_path, monkeypatch):
        """显式传入的 config_path 优先于 BILI_CONFIG_PATH"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BILI_CONFIG_PATH", "/nonexistent/path.yaml")

        real_path = tmp_path / "real.yaml"
        real_path.write_text("crawler:\n  concurrency: 3\n", encoding="utf-8")

        cfg = load_config(str(real_path))
        assert cfg.crawler.concurrency == 3
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_config.py::TestLoadConfig -v`
Expected: FAIL — `load_config` not defined

#### Step 3: Write loader.py

Create `src/bilianalysis/config/loader.py`:

```python
"""配置加载：YAML 文件 + 环境变量。"""
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from bilianalysis.config.model import (
    AppConfig, CrawlerSection, AnalysisSection, DataSection
)


class _AppSettings(BaseSettings):
    """内部类：负责 env 覆盖和 YAML 数据合并。
       不绑定 yaml_file，由 load_config 手动读取 YAML。"""
    model_config = SettingsConfigDict(
        env_prefix="BILI_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()


def load_config(config_path: str | None = None) -> AppConfig:
    """加载应用配置。
    优先级：参数 > BILI_CONFIG_PATH env > 默认 config.yaml
    文件不存在时不报错，全部使用默认值。"""
    path = config_path or os.getenv("BILI_CONFIG_PATH", "config.yaml")

    yaml_data: dict[str, Any] = {}
    if Path(path).exists():
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if loaded:
                yaml_data = loaded

    settings = _AppSettings(**yaml_data)
    return AppConfig(
        crawler=settings.crawler,
        analysis=settings.analysis,
        data=settings.data,
    )
```

- [ ] **Step 4: Run loader tests**

Run: `uv run pytest tests/test_config.py::TestLoadConfig -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/config/loader.py tests/test_config.py
git commit -m "feat: add config loader with YAML + env support"
```

---

### Task 4: 完善 config/__init__.py 公开 API

**Files:**
- Modify: `src/bilianalysis/config/__init__.py`

#### Step 1: Write __init__.py

Replace `src/bilianalysis/config/__init__.py`:

```python
"""配置模块。提供 load_config() + AppConfig 数据模型。"""
from bilianalysis.config.model import (
    AppConfig, CrawlerSection, AnalysisSection, DataSection,
)
from bilianalysis.config.loader import load_config

__all__ = [
    "load_config",
    "AppConfig",
    "CrawlerSection",
    "AnalysisSection",
    "DataSection",
]
```

- [ ] **Step 2: Verify import chain**

Run: `uv run python -c "from bilianalysis.config import load_config, AppConfig, CrawlerSection; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/config/__init__.py
git commit -m "feat: complete config public API"
```

---

### Task 5: 集成到 pipeline.py

**Files:**
- Modify: `src/bilianalysis/crawler/pipeline.py`
- Modify: `src/bilianalysis/crawler/__init__.py`

#### Step 1: Modify pipeline.py

Replace `CrawlConfig` class definition (lines 20-25) and `run` signature (line 37):

```python
# 删除:
# class CrawlConfig(BaseModel):
#     mode: Literal["sequential", "concurrent"] = "sequential"
#     concurrency: int = 3
#     request_delay: float = 2.5
#     max_retries: int = 3
#     retry_delay: float = 1.0

# 新增导入:
from bilianalysis.config import CrawlerSection, load_config

# 修改 run 签名:
async def run(config: CrawlerSection | None = None) -> CrawlReport:
    """执行一次完整爬取。供外部模块调用。"""
    if config is None:
        config = load_config().crawler
    # ... 后续不变
```

Implement exact edits:

```python
# Edit 1: Remove CrawlConfig class (lines 20-25), replace with import
# In pipeline.py, replace the CrawlConfig class definition with:
```

Delete lines 20-25 (`CrawlConfig` class), and add the import after line 6 (`from typing import Literal`):

```python
from bilianalysis.config import CrawlerSection, load_config
```

Change line 37 from:
```python
async def run(config: CrawlConfig = CrawlConfig()) -> CrawlReport:
```
to:
```python
async def run(config: CrawlerSection | None = None) -> CrawlReport:
```

Add after line 39 (`crawled_count = 0`):
```python
    if config is None:
        config = load_config().crawler
```

Change line 130 from:
```python
async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlConfig) -> tuple[bool, str]:
```
to:
```python
async def _crawl_one(session: aiohttp.ClientSession, number: int,
                     config: CrawlerSection) -> tuple[bool, str]:
```

Also remove unused imports: `from pydantic import BaseModel` (line 8) — but check if `CrawlReport` still uses it. Yes, `CrawlReport` is also a BaseModel. So keep `from pydantic import BaseModel`.

- [ ] **Step 2: Update crawler/__init__.py**

Replace `from .pipeline import CrawlConfig, CrawlReport, run as CrawlRunner` with:
```python
from .pipeline import CrawlReport, run as CrawlRunner
```

Replace `__all__` if present, or ensure `CrawlRunner` and `CrawlReport` are still exported.

- [ ] **Step 3: Run existing tests to see what breaks**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — tests still import `CrawlConfig`

---

### Task 6: 更新测试文件

**Files:**
- Modify: `tests/test_pipeline.py`

#### Step 1: Replace CrawlConfig with CrawlerSection in test_pipeline.py

Change import:
```python
from bilianalysis.crawler import CrawlConfig, CrawlReport, CrawlRunner as run
```
to:
```python
from bilianalysis.crawler import CrawlReport, CrawlRunner as run
from bilianalysis.config import CrawlerSection
```

Change `TestCrawlConfig` class to `TestCrawlerSection`:
```python
class TestCrawlerSection:
    def test_defaults(self):
        cfg = CrawlerSection()
        assert cfg.mode == "sequential"
        assert cfg.concurrency == 3
        assert cfg.request_delay == 2.5
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 1.0

    def test_override(self):
        cfg = CrawlerSection(mode="concurrent", concurrency=5)
        assert cfg.mode == "concurrent"
        assert cfg.concurrency == 5
```

Replace all `CrawlConfig(` with `CrawlerSection(` in the file (5 occurrences in TestRun methods).

- [ ] **Step 2: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (36 + config tests)

- [ ] **Step 3: Commit**

```bash
git add src/bilianalysis/crawler/pipeline.py src/bilianalysis/crawler/__init__.py tests/test_pipeline.py
git commit -m "feat: integrate config system into crawler pipeline"
```

---

### Task 7: 最终验证

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Smoke test — import + load default config**

Run: `uv run python -c "from bilianalysis.config import load_config; c = load_config('nonexistent.yaml'); print(f'mode={c.crawler.mode}, engine={c.analysis.engine}')"`
Expected: `mode=sequential, engine=pandas`

- [ ] **Step 3: Smoke test — end-to-end import**

Run: `uv run python -c "from bilianalysis.crawler import CrawlRunner, CrawlReport; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Final commit**

```bash
git add . && git commit -m "chore: final verification for config feature"
```
