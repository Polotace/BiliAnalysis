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
        assert cfg.data.processed_dir == "data/processed"


import os
import yaml
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
