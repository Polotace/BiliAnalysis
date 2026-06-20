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
import app.api.tasks                  # noqa: F401  (triggers app-layer task registration)
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
