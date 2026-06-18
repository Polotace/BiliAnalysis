# app/cli/utils.py
"""Rich terminal rendering utilities."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def make_task_table(task_infos: list[dict]) -> Table:
    """Render a table of registered Tasks."""
    table = Table(title="Available Tasks", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    for info in task_infos:
        table.add_row(info["name"], info.get("description", ""))
    return table


def make_pipeline_table(pipelines: dict) -> Table:
    """Render a table of configured Pipelines."""
    table = Table(title="Pipelines", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule", style="yellow")
    table.add_column("Steps", style="green")
    for name, pl in pipelines.items():
        schedule_str = pl.schedule or "manual only"
        steps_str = " -> ".join(pl.steps[:5])
        if len(pl.steps) > 5:
            steps_str += f" ...(+{len(pl.steps) - 5})"
        table.add_row(name, schedule_str, steps_str)
    return table


def make_serve_banner(config) -> Panel:
    """Render the serve startup banner."""
    lines = [
        "[bold cyan]BiliAnalysis Scheduler v0.1.0[/bold cyan]",
        "-" * 45,
        f"Engine: [yellow]{config.analysis.engine}[/yellow]",
        f"Pipelines: [green]{len(config.scheduler.pipelines)}[/green]",
        "",
    ]
    for name, pl in config.scheduler.pipelines.items():
        cron_hint = pl.schedule or "manual only"
        steps_short = "->".join(pl.steps[:5])
        lines.append(f"  [cyan]{name:<8}[/cyan] {cron_hint:<16} {steps_short}")
    return Panel("\n".join(lines), box=box.ROUNDED, title="Scheduler Started")
