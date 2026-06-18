"""测试调度系统。"""
import pytest
import yaml
from bilianalysis.config.model import AppConfig, SchedulerConfig, PipelineConfig
from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register, get_task, list_tasks, clear_registry


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


class TestTaskABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Task()

    def test_concrete_task_instantiable(self):
        @register("_test_dummy")
        class DummyTask(Task):
            name = "_test_dummy"
            async def run(self, ctx):
                return TaskResult(task_name="dummy", status="success", duration_seconds=0)

        task = DummyTask()
        assert task.name == "_test_dummy"
        clear_registry()

    def test_task_result_model(self):
        result = TaskResult(task_name="crawl", status="success", duration_seconds=1.5,
                            output={"crawled": 3})
        assert result.task_name == "crawl"
        assert result.output["crawled"] == 3
        assert result.error is None

    def test_task_result_failed(self):
        result = TaskResult(task_name="crawl", status="failed", duration_seconds=0.2,
                            error="Connection timeout")
        assert result.status == "failed"
        assert "timeout" in result.error


class TestRegistry:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    def test_register_and_get(self):
        @register("_test_crawl")
        class TestCrawlTask(Task):
            name = "_test_crawl"
            async def run(self, ctx):
                return TaskResult(task_name="crawl", status="success", duration_seconds=0)

        cls = get_task("_test_crawl")
        assert cls is TestCrawlTask

    def test_get_missing_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_task("nonexistent")

    def test_list_tasks_sorted(self):
        @register("_test_b")
        class TaskB(Task):
            name = "_test_b"
            async def run(self, ctx):
                return TaskResult(task_name="b", status="success", duration_seconds=0)

        @register("_test_a")
        class TaskA(Task):
            name = "_test_a"
            async def run(self, ctx):
                return TaskResult(task_name="a", status="success", duration_seconds=0)

        names = list_tasks()
        assert names == ["_test_a", "_test_b"]
