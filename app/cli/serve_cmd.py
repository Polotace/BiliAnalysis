"""bilianalysis serve - start the API server."""
import typer

serve_app = typer.Typer(name="serve", help="Start the API server")


def main():
    """Entry point for bilianalysis-serve script (no typer, plain Python)."""
    import uvicorn
    from bilianalysis.config import load_config
    from app.api import create_app

    config = load_config()
    app = create_app(config)

    print(f"BiliAnalysis API v0.1.0")
    print(f"  API:  http://127.0.0.1:8080")
    print(f"  Docs: http://127.0.0.1:8080/docs")
    print(f"  Engine: {config.analysis.engine}")
    print()

    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


@serve_app.callback(invoke_without_command=True)
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Listen port"),
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Start the BiliAnalysis API server."""
    import uvicorn
    from bilianalysis.config import load_config
    from app.api import create_app

    config = load_config(config_path)
    app = create_app(config)

    print(f"BiliAnalysis API v0.1.0")
    print(f"  API:  http://127.0.0.1:{port}")
    print(f"  Docs: http://127.0.0.1:{port}/docs")
    print(f"  Engine: {config.analysis.engine}")
    print()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
