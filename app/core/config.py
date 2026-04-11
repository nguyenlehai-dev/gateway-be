from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gateway Backend"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./gateway.db"
    cors_origins: str = ""
    auth_enabled: bool = False
    auth_tokens: str = ""
    auth_secret_key: str = "change-me-gateway-auth-secret"
    auth_access_token_ttl_minutes: int = 480
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "ChangeMe123!"
    bootstrap_admin_full_name: str = "Gateway Administrator"
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    provider_timeout_seconds: float = 300.0
    provider_max_retries: int = 1
    provider_retry_base_delay_seconds: float = 1.0
    sync_provider_timeout_seconds: float = 45.0
    sync_provider_max_retries: int = 0
    sync_force_async_functions: str = ""
    async_job_default_max_attempts: int = 3
    async_job_retry_base_delay_seconds: float = 5.0
    async_job_retry_max_delay_seconds: float = 60.0
    async_job_batch_size: int = 20
    webhook_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="GATEWAY_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
