from collections import deque
from dataclasses import dataclass
from time import time

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.config import get_settings
from app.models.gateway_api_key import GatewayApiKey
from app.models.pool import Pool
from app.services.auth_service import decode_access_token, verify_secret

bearer_scheme = HTTPBearer(auto_error=False)
_rate_limit_store: dict[str, deque[float]] = {}


@dataclass
class AuthContext:
    role: str
    token: str
    user_id: int | None = None
    username: str | None = None
    pool_id: int | None = None


@dataclass
class GatewayKeyContext:
    key: str
    api_key_id: int | None
    user_id: int | None
    pool_id: int
    pool_name: str
    pool_code: str
    vendor_id: int
    vendor_name: str
    vendor_code: str
    key_masked: str
    key_name: str | None = None


def mask_secret(value: str, visible_prefix: int = 4, visible_suffix: int = 2) -> str:
    if len(value) <= visible_prefix + visible_suffix:
        return "*" * len(value)

    return f"{value[:visible_prefix]}{'*' * (len(value) - visible_prefix - visible_suffix)}{value[-visible_suffix:]}"


def _parse_auth_tokens(raw_tokens: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    if not raw_tokens.strip():
        return tokens

    for pair in raw_tokens.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        role, token = pair.split(":", 1)
        tokens[token.strip()] = role.strip()
    return tokens


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthContext(role="admin", token="dev-mode", username="dev-mode")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
        return AuthContext(
            role=str(payload["role"]),
            token=credentials.credentials,
            user_id=int(payload["sub"]),
            username=str(payload["username"]),
            pool_id=int(payload["pool_id"]) if payload.get("pool_id") is not None else None,
        )
    except HTTPException:
        pass

    token_map = _parse_auth_tokens(settings.auth_tokens)
    role = token_map.get(credentials.credentials)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    return AuthContext(role=role, token=credentials.credentials, username=f"{role}-token")


def get_optional_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthContext(role="admin", token="dev-mode", username="dev-mode")

    if credentials is None:
        return None

    return get_auth_context(credentials)


def resolve_gateway_key_context(db: Session, gateway_api_key: str) -> GatewayKeyContext | None:
    candidate = gateway_api_key.strip()
    if not candidate:
        return None

    api_keys = db.execute(select(GatewayApiKey).where(GatewayApiKey.status == "active").order_by(GatewayApiKey.id.desc())).scalars().all()
    for api_key in api_keys:
        if not verify_secret(candidate, api_key.key_hash):
            continue

        pool = api_key.pool
        vendor = pool.vendor if pool is not None else None
        user = api_key.user
        if pool is None or vendor is None or pool.status != "active" or vendor.status != "active":
            continue
        if user is None or user.status != "active":
            continue

        return GatewayKeyContext(
            key=candidate,
            api_key_id=api_key.id,
            user_id=user.id,
            pool_id=pool.id,
            pool_name=pool.name,
            pool_code=pool.code,
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            vendor_code=vendor.code,
            key_masked=api_key.key_masked,
            key_name=api_key.name,
        )

    pools = db.execute(select(Pool).where(Pool.status == "active").order_by(Pool.id.asc())).scalars().all()
    for pool in pools:
        config = pool.config_json or {}
        configured_hash = config.get("gateway_api_key_hash")
        if not configured_hash or not verify_secret(candidate, configured_hash):
            continue

        vendor = pool.vendor
        if vendor is None or vendor.status != "active":
            continue

        return GatewayKeyContext(
            key=candidate,
            api_key_id=None,
            user_id=None,
            pool_id=pool.id,
            pool_name=pool.name,
            pool_code=pool.code,
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            vendor_code=vendor.code,
            key_masked=config.get("gateway_api_key_masked") or mask_secret(candidate),
            key_name=config.get("gateway_api_key_name"),
        )
    return None


def get_optional_gateway_key_context(
    gateway_api_key: str | None = Header(default=None, alias="X-Gateway-Api-Key"),
    db: Session = Depends(db_session),
) -> GatewayKeyContext | None:
    if not gateway_api_key:
        return None
    return resolve_gateway_key_context(db, gateway_api_key)


def get_gateway_key_context(
    gateway_api_key: str | None = Header(default=None, alias="X-Gateway-Api-Key"),
    db: Session = Depends(db_session),
) -> GatewayKeyContext:
    if not gateway_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing gateway API key")

    context = resolve_gateway_key_context(db, gateway_api_key)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway API key")
    return context


def require_operator(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role not in {"admin", "operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
    return auth


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return auth


def require_operator_or_gateway_key(
    auth: AuthContext | None = Depends(get_optional_auth_context),
    gateway_key: GatewayKeyContext | None = Depends(get_optional_gateway_key_context),
) -> AuthContext | GatewayKeyContext:
    if gateway_key is not None:
        return gateway_key
    if auth is not None:
        if auth.role not in {"admin", "operator"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
        return auth
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")


def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    client_key = request.client.host if request.client else "unknown"
    now = time()
    bucket = _rate_limit_store.setdefault(client_key, deque())

    while bucket and bucket[0] <= now - settings.rate_limit_window_seconds:
        bucket.popleft()

    if len(bucket) >= settings.rate_limit_requests:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    bucket.append(now)
