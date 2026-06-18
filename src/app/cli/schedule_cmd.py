# app/cli/schedule_cmd.py
"""schedule subcommand group - run / serve / list / test."""
import asyncio

import typer
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from bilianalysis.config import load_config
from bilianalysis.scheduler.registry import list_tasks, get_task
from bilianalysis.scheduler.runner import PipelineRunner
from bilianalysis.scheduler.cron_service import CronService
import bilianalysis.scheduler.builtins  # noqa: F401  (triggers task registration)
from app.cli.utils import (
    console, make_task_table, make_pipeline_table, make_serve_banner,
)

schedule_app = typer.Typer(name="schedule", help="Scheduler management")

_TASK_DESCRIPTIONS = {
    "crawl": "Crawl Bilibili weekly must-watch data",
    "clean_data": "Clean data -> 5 Parquet tables",
    "statistics": "Statistical analysis (overall/category/creator/weekly)",
    "clustering": "KMeans clustering (k=3)",
    "prediction": "Linear regression prediction (views/likes)",
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


@schedule_app.command("serve")
def serve_cmd(
    port: int = typer.Option(8080, "--port", "-p", help="API listen port"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Start the scheduler daemon (cron + HTTP API)."""
    import uvicorn
    from app.api import create_scheduler_app

    config = load_config(config_path)
    console.print(make_serve_banner(config))
    console.print(f"\n  API:   [cyan]http://127.0.0.1:{port}[/cyan]")
    console.print(f"  Docs:  [cyan]http://127.0.0.1:{port}/docs[/cyan]\n")

    service = CronService(config)
    service.setup_schedule()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    service.start_scheduler(loop)

    app = create_scheduler_app(service)
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        service.stop()


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
