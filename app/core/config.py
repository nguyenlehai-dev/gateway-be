from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gateway BE"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://gateway:gateway@localhost:5432/gateway"
    cors_origins: list[str] = ["http://localhost:5173"]
    default_headless: bool = True
    default_concurrency: int = 2
    playwright_timeout_ms: int = 120000
    frontend_dist: str = "/home/vpsroot/projects/gateway-fe/dist"
    auth_secret_key: str = "change-me-gateway-secret"
    admin_username: str = "admin"
    admin_password: str = "Admin@123456"
    admin_display_name: str = "Prod Gateway Admin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
