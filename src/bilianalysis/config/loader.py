"""配置加载：YAML 文件 + 环境变量。"""
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from .model import (
    AppConfig, CrawlerSection, AnalysisSection, DataSection,
    SchedulerConfig,
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
    scheduler: SchedulerConfig = SchedulerConfig()


def _merge_env_vars(data: dict[str, Any]) -> None:
    """读取 BILI_* 环境变量并合并到 data 字典中（环境变量优先）。"""
    for key, value in os.environ.items():
        if not key.startswith("BILI_"):
            continue
        rest = key[5:]  # 去掉 "BILI_" 前缀
        parts = rest.split("__")
        if len(parts) == 2:
            section, field = parts
            section_lower = section.lower()
            field_lower = field.lower()
            if section_lower not in data:
                data[section_lower] = {}
            data[section_lower][field_lower] = value


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

    # 环境变量覆盖 YAML 设置（手动合并，因为 pydantic-settings 中 kwargs 优先级高于 env）
    _merge_env_vars(yaml_data)

    settings = _AppSettings(**yaml_data)
    return AppConfig(
        crawler=settings.crawler,
        analysis=settings.analysis,
        data=settings.data,
        scheduler=settings.scheduler,
    )
