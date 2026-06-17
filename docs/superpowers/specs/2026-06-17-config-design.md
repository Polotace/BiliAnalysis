# 配置功能设计

Date: 2026-06-17 | Status: approved

## 概述

实现全项目统一配置系统。支持 YAML 文件 + 环境变量覆盖，覆盖爬虫、分析引擎、数据路径等模块。

## 需求

| 需求 | 决定 |
|------|------|
| 范围 | 全项目（爬虫 + 分析引擎 + 数据路径 + 未来扩展） |
| 格式 | YAML |
| 优先级 | 文件优先 → 环境变量覆盖 |
| 路径 | 默认 `config.yaml`，`BILI_CONFIG_PATH` env 覆盖 |
| 文件不存在 | 全部默认值，不报错 |

## 文件结构

```
src/bilianalysis/config/
├── __init__.py          # 公开 API：load_config()、AppConfig、子节模型
├── model.py             # Pydantic 模型定义（纯数据，零 I/O）
└── loader.py            # pydantic-settings 加载（YAML + env）

config.yaml              # 项目根目录，用户可选
```

## 模型设计

### model.py

```python
from pydantic import BaseModel
from typing import Literal


class CrawlerSection(BaseModel):
    mode: Literal["sequential", "concurrent"] = "sequential"
    concurrency: int = 3
    request_delay: float = 2.5
    max_retries: int = 3
    retry_delay: float = 1.0


class AnalysisSection(BaseModel):
    engine: Literal["pandas", "spark"] = "pandas"


class DataSection(BaseModel):
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    reports_dir: str = "data/reports"


class AppConfig(BaseModel):
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
```

### 对应的 config.yaml

```yaml
crawler:
  mode: concurrent
  concurrency: 5

analysis:
  engine: spark

data:
  raw_dir: data/raw
```

用户只写需要覆盖的字段，其余使用默认值。

## 加载机制

### loader.py

基于 `pydantic-settings` 的 `BaseSettings`：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from bilianalysis.config.model import CrawlerSection, AnalysisSection, DataSection, AppConfig


class _AppSettings(BaseSettings):
    """内部类：负责 env 覆盖和 YAML 数据合并。不绑定 yaml_file，由 load_config 手动读取。"""
    model_config = SettingsConfigDict(
        env_prefix="BILI_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    crawler: CrawlerSection = CrawlerSection()
    analysis: AnalysisSection = AnalysisSection()
    data: DataSection = DataSection()
```

### load_config 函数

```python
import os
import yaml
from pathlib import Path
from typing import Any

def load_config(config_path: str | None = None) -> AppConfig:
    """加载应用配置。
    优先级：参数 > BILI_CONFIG_PATH env > 默认 config.yaml
    文件不存在时不报错，全部使用默认值。"""
    path = config_path or os.getenv("BILI_CONFIG_PATH", "config.yaml")

    yaml_data: dict[str, Any] = {}
    if Path(path).exists():
        with open(path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    settings = _AppSettings(**yaml_data)
    return AppConfig(
        crawler=settings.crawler,
        analysis=settings.analysis,
        data=settings.data,
    )
```

### 环境变量覆盖

| env 变量 | 效果 |
|----------|------|
| `BILI_CRAWLER__MODE=concurrent` | 覆盖 `crawler.mode` |
| `BILI_CRAWLER__CONCURRENCY=10` | 覆盖 `crawler.concurrency` |
| `BILI_ANALYSIS__ENGINE=spark` | 覆盖 `analysis.engine` |
| `BILI_DATA__RAW_DIR=/mnt/data/raw` | 覆盖 `data.raw_dir` |
| `BILI_CONFIG_PATH=/etc/bil/prod.yaml` | 自定义配置文件路径 |

### __init__.py 公开 API

```python
from bilianalysis.config.model import AppConfig, CrawlerSection, AnalysisSection, DataSection
from bilianalysis.config.loader import load_config

__all__ = ["load_config", "AppConfig", "CrawlerSection", "AnalysisSection", "DataSection"]
```

## pipeline 集成

### 改前

```python
# pipeline.py
class CrawlConfig(BaseModel): ...

async def CrawlRunner(config: CrawlConfig = CrawlConfig()) -> CrawlReport:
```

### 改后

```python
# pipeline.py
from bilianalysis.config import CrawlerSection, load_config

async def CrawlRunner(config: CrawlerSection | None = None) -> CrawlReport:
    if config is None:
        config = load_config().crawler
    # 后续逻辑不变，CrawlerSection 字段名与旧 CrawlConfig 完全兼容
```

### 改动清单

| 文件 | 改动 |
|------|------|
| `pipeline.py` | 删除 `CrawlConfig`，`CrawlRunner` 接受 `CrawlerSection \| None`，`None` 时自动加载 |
| `crawler/__init__.py` | 导出 `CrawlConfig` → `CrawlerSection`（或保留别名） |
| 测试文件 | `CrawlConfig(...)` → `CrawlerSection(...)` |
| `storage.py` | 暂不改动（`DATA_DIR` 迁移后续 PR 处理） |

### 用法

```python
# 1. 默认加载（读 config.yaml + env）
from bilianalysis.crawler import CrawlRunner
report = await CrawlRunner()

# 2. 代码显式传入覆盖
from bilianalysis.config import CrawlerSection
config = CrawlerSection(mode="concurrent", concurrency=10)
report = await CrawlRunner(config)

# 3. 自定义配置文件
from bilianalysis.config import load_config
app = load_config("/path/to/prod.yaml")
report = await CrawlRunner(app.crawler)
```

## 依赖

- `pydantic-settings` — 新增：`uv add pydantic-settings`
- `pyyaml` — pydantic-settings 的 YAML 后端：`uv add pyyaml`

## 不在范围内

- 不迁移 `storage.py` 的 `DATA_DIR`（后续 PR）
- 不改现有 `ProgressFile` 模型
- 不做多文件合并（仅单 YAML）
- 不做热加载 / 文件监控
