"""Application settings from environment."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Orchestrator configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ihms_base_url: str = "http://localhost:8080"
    ecops_base_url: str = "http://localhost:8002"
    ecops_bearer_token: str = ""

    catalog_source: Literal["json", "ihms"] = "ihms"
    catalog_path: Path = Path("catalog/products.json")
    ecops_mapping_path: Path = Path("catalog/ecops-mapping.json")
    catalog_fallback_to_json: bool = False

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ]

    ihms_connect_timeout: float = 2.0
    ihms_read_timeout: float = 5.0
    ihms_fulfill_optional: bool = True
    ecops_connect_timeout: float = 2.0
    ecops_read_timeout: float = 10.0

    log_level: str = "INFO"
    log_json: bool = True


def get_settings() -> Settings:
    return Settings()
