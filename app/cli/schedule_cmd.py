# app/cli/schedule_cmd.py
"""schedule subcommand group - run / list / test."""
import asyncio

import typer
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from bilianalysis.config import load_config
from bilianalysis.scheduler.registry import list_tasks, get_task
from bilianalysis.scheduler.runner import PipelineRunner
import bilianalysis.scheduler.builtins  # noqa: F401  (triggers task registration)
import api.tasks                  # noqa: F401  (triggers app-layer task registration)
from cli.utils import (
    console, make_task_table, make_pipeline_table,
)

schedule_app = typer.Typer(name="schedule", help="Scheduler management")

_TASK_DESCRIPTIONS = {
    "crawl": "爬取Bilibili每周必看数据",
    "clean_data": "清洗数据-> 5个Parquet表",
    "statistics": "统计分析（整体/类别/创作者/周报）",
    "clustering": "KMeans聚类（k=3）",
    "prediction": "线性回归预测（观看数/点赞数）",
}


@schedule_app.command("list")
def list_cmd(
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """List all available Tasks and Pipelines."""
    config = load_config(config_path)

    task_infos = [
        {"name": name, "description": _TASK_DESCRIPTIONS.get(name, "")}
        for name in list_tasks()
    ]
    console.print(make_task_table(task_infos))

    if config.scheduler.pipelines:
        console.print(make_pipeline_table(config.scheduler.pipelines))
    else:
        console.print("[dim]No pipelines configured in config.yaml[/dim]")


@schedule_app.command("run")
def run_cmd(
    pipeline: str = typer.Option(..., "--pipeline", "-p", help="Pipeline name"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Manually trigger a pipeline execution."""
    config = load_config(config_path)
    if pipeline not in config.scheduler.pipelines:
        console.print(f"[red]Pipeline '{pipeline}' not found in config[/red]")
        raise typer.Exit(1)

    pl = config.scheduler.pipelines[pipeline]
    runner = PipelineRunner(config)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )
    progress_ids = {}
    for step in pl.steps:
        progress_ids[step] = progress.add_task(step, total=None)

    async def _run():
        record = await runner.run(pipeline, trigger="manual")
        for i, result in enumerate(record.step_results):
            step = pl.steps[i] if i < len(pl.steps) else "unknown"
            pid = progress_ids.get(step)
            if result.status == "success":
                desc = f"[green]*[/green] {step:<15} {result.duration_seconds:.1f}s"
                if result.output:
                    key_vals = " ".join(f"{k}={v}" for k, v in list(result.output.items())[:3])
                    desc += f"  [dim]{key_vals}[/dim]"
                if pid is not None:
                    progress.update(pid, description=desc)
            elif result.status == "failed":
                if pid is not None:
                    progress.update(pid, description=f"[red]x[/red] {step:<15} [red]{result.error or 'failed'}[/red]")
        return record

    with Live(progress, console=console, refresh_per_second=4):
        record = asyncio.run(_run())

    status_color = "green" if record.status == "success" else "red"
    console.print(f"\n[{status_color}]Pipeline '{pipeline}': {record.status}[/{status_color}]")


@schedule_app.command("run-task")
def run_task_cmd(
    task: str = typer.Option(..., "--task", "-t", help="Task name to run"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Run a single task independently (not as part of a pipeline)."""
    import asyncio
    import time
    from bilianalysis.scheduler.task import TaskContext
    from bilianalysis.engine import create_engine

    import bilianalysis.scheduler.builtins  # noqa: F401
    import api.tasks                  # noqa: F401

    config = load_config(config_path)
    try:
        task_cls = get_task(task)
    except KeyError:
        console.print(f"[red]Task '{task}' not found. Available: {', '.join(list_tasks())}[/red]")
        raise typer.Exit(1)

    ctx = TaskContext(config=config)
    engine = create_engine(config)
    ctx.engine = engine

    try:
        console.print(f"[bold]Running task: {task}[/bold]")
        start = time.monotonic()
        result = asyncio.run(task_cls().run(ctx))
        elapsed = time.monotonic() - start
    finally:
        if hasattr(engine, "_spark"):
            spark = engine._spark
            if spark is not None:
                try:
                    spark.stop()
                except Exception:
                    pass

    if result.status == "success":
        console.print(f"[green]✔ {task} completed in {elapsed:.1f}s[/green]")
        if result.output:
            for k, v in result.output.items():
                console.print(f"  {k}: {v}")
    else:
        console.print(f"[red]✘ {task} failed: {result.error}[/red]")


@schedule_app.command("check-raw")
def check_raw_cmd(
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Compare local data/raw/ with HDFS /user/hadoop/bilibili/raw/."""
    import json
    config = load_config(config_path)
    if config.analysis.engine != "spark":
        console.print("[yellow]Not using Spark engine — skipping[/yellow]")
        return

    from bilianalysis.engine.spark_engine import SparkEngine
    engine = SparkEngine(
        config.data,
        spark_remote=config.analysis.spark_remote,
        webhdfs_url=config.analysis.webhdfs_url,
    )
    result = engine.check_raw_sync()

    console.print(f"\n[bold]本地 files:[/bold] {len(result['local'])}")
    if result["hdfs"] is None:
        console.print("[red]HDFS unreachable![/red]")
        return

    console.print(f"[bold]HDFS files:[/bold] {len(result['hdfs'])}")
    console.print(f"[bold]同步:[/bold] {len(result['in_sync'])}")
    if result["local_only"]:
        console.print(f"[yellow]仅在本地 ({len(result['local_only'])}):[/yellow]")
        for f in result["local_only"]:
            console.print(f"  {f}")
    if result.get("hdfs_only"):
        console.print(f"[blue]仅在 HDFS ({len(result['hdfs_only'])}):[/blue]")
        for f in result["hdfs_only"]:
            console.print(f"  {f}")
    if not result["local_only"] and not result.get("hdfs_only", []):
        console.print("[green]全部同步 ✓[/green]")


@schedule_app.command("test")
def test_cmd(
    pipeline: str = typer.Option(..., "--pipeline", "-p", help="Pipeline name"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Validate pipeline configuration (imports and step names only)."""
    config = load_config(config_path)
    if pipeline not in config.scheduler.pipelines:
        console.print(f"[red]Pipeline '{pipeline}' not found in config[/red]")
        raise typer.Exit(1)

    pl = config.scheduler.pipelines[pipeline]
    console.print(f"[bold]Checking pipeline: {pipeline}[/bold]")
    for step in pl.steps:
        try:
            get_task(step)
            console.print(f"  [green]OK[/green] {step}")
        except KeyError as e:
            console.print(f"  [red]FAIL[/red] {step} - {e}")
            raise typer.Exit(1)
    console.print(f"\n[green]All {len(pl.steps)} steps valid.[/green]")
