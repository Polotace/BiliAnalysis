"""bilianalysis serve - start the API server."""
import typer

serve_app = typer.Typer(name="serve", help="Start the API server")


@serve_app.callback(invoke_without_command=True)
def serve(
    port: int = 8080,
    config_path: str = "config.yaml",
):
    """Start the BiliAnalysis API server.

    Works both via typer CLI (bilianalysis serve --port 8080)
    and as a direct script entry point (bilianalysis-serve).
    """
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
