"""Application settings from environment."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Orchestrator configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ihms_base_url: str = "http://localhost:8080"
    ecops_base_url: str = "http://localhost:8002"
    ecops_bearer_token: str = ""

    catalog_path: Path = Path("catalog/products.json")

    ihms_connect_timeout: float = 2.0
    ihms_read_timeout: float = 5.0
    ecops_connect_timeout: float = 2.0
    ecops_read_timeout: float = 10.0


def get_settings() -> Settings:
    return Settings()
