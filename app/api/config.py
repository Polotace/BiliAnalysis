"""FastAPI application settings — database URL lives here, not in global config.yaml."""
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/biliinsight"
    database_pool_size: int = 5
    admin_api_key: str = ""

    model_config = {"env_file": ".env"}
