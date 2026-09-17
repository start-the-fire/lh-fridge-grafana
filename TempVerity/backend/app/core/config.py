from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TEMPVERITY_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "TempVerity"
    app_version: str = "1.5.0"
    support_email: str = "placeholder@placeholder.com"  # Replace via TEMPVERITY_SUPPORT_EMAIL before deployment.
    grafana_url: str = ""
    db_path: Path = Field(default=Path("./tempverity.sqlite3"))
    data_dir: Path = Field(default=Path("./data"))
    frontend_dist: Path = Field(default=Path("./frontend/dist"))
    api_base_path: str = "/api"
    smtp_from: str = "alerts@example.invalid"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    admin_password: str = "change-me-before-enabling-auth"
    session_lifetime_days: int = 30
    read_only: bool = True
    influx_enabled: bool = False
    influx_url: str = ""
    influx_org: str = ""
    influx_bucket: str = ""
    influx_token: str = ""
    grafana_embeds_enabled: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
