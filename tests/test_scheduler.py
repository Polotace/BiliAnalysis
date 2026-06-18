"""测试调度系统。"""
import pytest
import yaml
from bilianalysis.config.model import AppConfig, SchedulerConfig, PipelineConfig


class TestSchedulerConfig:
    def test_default_config(self):
        cfg = SchedulerConfig()
        assert cfg.pipelines == {}

    def test_pipeline_config_defaults(self):
        pc = PipelineConfig()
        assert pc.schedule == ""
        assert pc.steps == []
        assert pc.step_failure == "stop"
        assert pc.max_retries == 0

    def test_yaml_round_trip(self):
        yaml_str = """
scheduler:
  pipelines:
    full:
      schedule: "0 12 * * 6"
      steps:
        - crawl
        - clean_data
        - statistics
        - clustering
        - prediction
      step_failure: stop
      max_retries: 0
    quick:
      schedule: "0 8 * * *"
      steps:
        - crawl
        - statistics
      step_failure: skip
      max_retries: 1
"""
        data = yaml.safe_load(yaml_str)
        cfg = AppConfig(**data)
        assert len(cfg.scheduler.pipelines) == 2
        full = cfg.scheduler.pipelines["full"]
        assert full.schedule == "0 12 * * 6"
        assert len(full.steps) == 5
        assert full.step_failure == "stop"
        quick = cfg.scheduler.pipelines["quick"]
        assert quick.step_failure == "skip"
        assert quick.max_retries == 1
