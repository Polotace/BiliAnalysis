"""测试调度系统。"""
from datetime import datetime, timezone

import pytest
import yaml
from bilianalysis.config.model import AppConfig, SchedulerConfig, PipelineConfig
from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register, get_task, list_tasks, clear_registry
from bilianalysis.scheduler.models import RunRecord
from bilianalysis.scheduler.runner import PipelineRunner


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


# ——— PipelineRunner 测试用 mock tasks ———
@register("_mock_success")
class _MockSuccessTask(Task):
    name = "_mock_success"
    async def run(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(task_name=self.name, status="success", duration_seconds=0.1,
                          output={"value": 42})


@register("_mock_fail")
class _MockFailTask(Task):
    name = "_mock_fail"
    async def run(self, ctx: TaskContext) -> TaskResult:
        return TaskResult(task_name=self.name, status="failed", duration_seconds=0.1,
                          error="mock error")


class TestRunRecord:
    def test_run_record_defaults(self):
        record = RunRecord(pipeline="full", trigger="manual")
        assert record.status == "running"
        assert record.pipeline == "full"
        assert len(record.run_id) == 12
        assert record.finished_at is None

    def test_run_record_completed(self):
        record = RunRecord(pipeline="quick", trigger="cron")
        record.status = "success"
        record.finished_at = datetime.now(timezone.utc)
        assert record.status == "success"


class TestPipelineRunner:
    def setup_method(self):
        clear_registry()
        register("_mock_success")(_MockSuccessTask)
        register("_mock_fail")(_MockFailTask)

    def teardown_method(self):
        clear_registry()

    def _make_config(self, steps, step_failure="stop", max_retries=0):
        return AppConfig(
            scheduler=SchedulerConfig(
                pipelines={
                    "test": PipelineConfig(
                        steps=steps,
                        step_failure=step_failure,
                        max_retries=max_retries,
                    )
                }
            )
        )

    @pytest.mark.asyncio
    async def test_all_success(self):
        config = self._make_config(["_mock_success", "_mock_success"])
        runner = PipelineRunner(config)
        record = await runner.run("test")
        assert record.status == "success"
        assert len(record.step_results) == 2
        assert all(r.status == "success" for r in record.step_results)

    @pytest.mark.asyncio
    async def test_stop_on_failure(self):
        config = self._make_config(["_mock_success", "_mock_fail", "_mock_success"],
                                   step_failure="stop")
        runner = PipelineRunner(config)
        record = await runner.run("test")
        assert record.status == "failed"
        assert len(record.step_results) == 2
        assert record.step_results[0].status == "success"
        assert record.step_results[1].status == "failed"

    @pytest.mark.asyncio
    async def test_skip_on_failure(self):
        config = self._make_config(["_mock_success", "_mock_fail", "_mock_success"],
                                   step_failure="skip")
        runner = PipelineRunner(config)
        record = await runner.run("test")
        assert len(record.step_results) == 3
        assert record.step_results[0].status == "success"
        assert record.step_results[1].status == "failed"
        assert record.step_results[2].status == "success"
        assert record.status == "failed"

    @pytest.mark.asyncio
    async def test_missing_pipeline_raises_keyerror(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        runner = PipelineRunner(config)
        with pytest.raises(KeyError):
            await runner.run("nonexistent")


from unittest.mock import AsyncMock, patch


class TestBuiltinTasks:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    @pytest.mark.asyncio
    async def test_crawl_task_success(self):
        from bilianalysis.scheduler.builtins.crawl_task import CrawlTask
        from bilianalysis.crawler import CrawlReport

        task = CrawlTask()
        ctx = TaskContext(
            config=AppConfig(scheduler=SchedulerConfig(pipelines={})),
        )

        mock_report = CrawlReport(
            total=50, crawled=3, skipped=47, failed=0,
            failed_weeks={}, duration_seconds=2.5,
        )
        with patch("bilianalysis.crawler.CrawlRunner",
                   new_callable=AsyncMock) as mock_runner:
            mock_runner.return_value = mock_report
            result = await task.run(ctx)

        assert result.status == "success"
        assert result.output["crawled"] == 3
        assert result.output["skipped"] == 47

    @pytest.mark.asyncio
    async def test_crawl_task_failure(self):
        from bilianalysis.scheduler.builtins.crawl_task import CrawlTask

        task = CrawlTask()
        ctx = TaskContext(
            config=AppConfig(scheduler=SchedulerConfig(pipelines={})),
        )
        with patch("bilianalysis.crawler.CrawlRunner",
                   new_callable=AsyncMock) as mock_runner:
            mock_runner.side_effect = RuntimeError("network error")
            result = await task.run(ctx)

        assert result.status == "failed"
        assert "network error" in result.error


from bilianalysis.scheduler.cron_service import CronService


class TestCronService:
    def test_history_starts_empty(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        service = CronService(config)
        assert service.history == []

    def test_setup_schedule_no_pipelines(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        service = CronService(config)
        service.setup_schedule()  # should not raise

    def test_stop_cleanup(self):
        config = AppConfig(scheduler=SchedulerConfig(pipelines={}))
        service = CronService(config)
        service.stop()  # should not raise


from typer.testing import CliRunner
from app.cli import app as cli_app
import sys


class TestCLI:
    def setup_method(self):
        """Re-register builtin tasks after prior tests may have cleared the registry."""
        from bilianalysis.scheduler.registry import clear_registry
        clear_registry()
        for mod_name in list(sys.modules):
            if mod_name.startswith("bilianalysis.scheduler.builtins"):
                del sys.modules[mod_name]
        import bilianalysis.scheduler.builtins  # noqa: F401

    def test_list_command_outputs_tasks(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "list"])
        assert result.exit_code == 0
        assert "crawl" in result.stdout
        assert "statistics" in result.stdout

    def test_test_command_valid_pipeline(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_data = {
            "scheduler": {
                "pipelines": {
                    "full": {"steps": ["crawl", "statistics"]}
                }
            }
        }
        config_path.write_text(yaml.dump(config_data))
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "test", "--pipeline", "full",
                                          "--config", str(config_path)])
        assert result.exit_code == 0
        assert "All 2 steps valid" in result.stdout

    def test_build_warehouse_task_registered(self):
        """build_warehouse task is registered and importable."""
        from bilianalysis.scheduler.registry import get_task
        task = get_task("build_warehouse")
        assert task is not None
        assert task.name == "build_warehouse"

    def test_test_command_invalid_step(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_data = {
            "scheduler": {
                "pipelines": {
                    "bad": {"steps": ["nonexistent_task"]}
                }
            }
        }
        config_path.write_text(yaml.dump(config_data))
        runner = CliRunner()
        result = runner.invoke(cli_app, ["schedule", "test", "--pipeline", "bad",
                                          "--config", str(config_path)])
        assert result.exit_code == 1
