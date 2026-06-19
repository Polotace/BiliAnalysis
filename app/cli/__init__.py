# app/cli/__init__.py
"""BiliAnalysis CLI - unified command-line entry point."""
import typer

app = typer.Typer(name="bilianalysis", help="Bilibili Weekly Must-Watch Data Analysis Platform")


def _register_schedule():
    """Lazy-register schedule subcommand."""
    from cli.schedule_cmd import schedule_app
    app.add_typer(schedule_app, name="schedule", help="Scheduler management")


_register_schedule()

from cli.serve_cmd import serve_app
app.add_typer(serve_app, name="serve", help="Start API server")
