from copy import deepcopy

from app.core.security import mask_secret
from app.services.auth_service import hash_secret


SENSITIVE_FIELDS = {"provider_api_key", "gateway_api_key_hash"}


def build_pool_config(
    *,
    timeout_seconds: int | None = None,
    provider: str | None = None,
    provider_api_key: str | None = None,
    provider_project_number: str | None = None,
    default_model: str | None = None,
    gateway_api_key: str | None = None,
    gateway_api_key_name: str | None = None,
    existing_config: dict | None = None,
) -> dict:
    config = deepcopy(existing_config or {})

    if timeout_seconds is not None:
        config["timeout_seconds"] = timeout_seconds
    if provider is not None:
        config["provider"] = provider
    if provider_api_key is not None:
        config["provider_api_key"] = provider_api_key.strip()
    if provider_project_number is not None:
        config["provider_project_number"] = provider_project_number.strip()
    if default_model is not None:
        config["default_model"] = default_model.strip()
    if gateway_api_key_name is not None:
        stripped_name = gateway_api_key_name.strip()
        if stripped_name:
            config["gateway_api_key_name"] = stripped_name
    if gateway_api_key is not None:
        stripped = gateway_api_key.strip()
        if stripped:
            config["gateway_api_key_hash"] = hash_secret(stripped)
            config["gateway_api_key_masked"] = mask_secret(stripped)

    return config


def sanitize_pool_config(config: dict | None) -> dict | None:
    if config is None:
        return None

    sanitized = deepcopy(config)
    provider_api_key = sanitized.pop("provider_api_key", None)
    gateway_api_key_hash = sanitized.pop("gateway_api_key_hash", None)

    if provider_api_key:
        sanitized["provider_api_key_masked"] = mask_secret(provider_api_key)
    if gateway_api_key_hash:
        sanitized["gateway_api_key_configured"] = True
    else:
        sanitized["gateway_api_key_configured"] = bool(sanitized.get("gateway_api_key_masked"))

    return sanitized
