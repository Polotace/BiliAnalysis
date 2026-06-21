"""Config endpoints: /api/config"""
from typing import Annotated

import yaml
from fastapi import APIRouter, Request, Depends, HTTPException

from bilianalysis.config.model import AppConfig
from api.deps import get_config, require_admin
from api.schemas import ConfigUpdateRequest

router = APIRouter(tags=["config"])


def _config_to_dict(config: AppConfig) -> dict:
    """Serialize AppConfig to a JSON-safe dict."""
    return {
        "crawler": config.crawler.model_dump(),
        "analysis": config.analysis.model_dump(),
        "data": config.data.model_dump(),
        "scheduler": config.scheduler.model_dump(),
    }


@router.get("/config")
async def get_config_endpoint(config: Annotated[AppConfig, Depends(get_config)]):
    """Return the current effective configuration."""
    return _config_to_dict(config)


@router.put("/config")
async def update_config(
    body: ConfigUpdateRequest,
    config: Annotated[AppConfig, Depends(get_config)],
    request: Request,
    _admin: None = Depends(require_admin),
):
    """Update runtime configuration, optionally persisting to config.yaml."""
    section_attr = body.section
    if not hasattr(config, section_attr):
        raise HTTPException(400, f"Unknown config section: {body.section}")

    target = getattr(config, section_attr)
    try:
        for key, value in body.values.items():
            if hasattr(target, key):
                setattr(target, key, value)
            else:
                raise HTTPException(
                    400, f"Unknown field '{key}' in section '{body.section}'"
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Failed to update config: {exc}")

    if body.persist:
        try:
            config_path = "config.yaml"
            full_config = _config_to_dict(config)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(full_config, f, allow_unicode=True, default_flow_style=False)
        except Exception as exc:
            raise HTTPException(500, f"Failed to write config.yaml: {exc}")

    return {"detail": f"Section '{body.section}' updated", "persisted": body.persist}
