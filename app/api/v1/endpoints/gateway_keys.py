import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import (
    AuthContext,
    GatewayKeyContext,
    get_optional_auth_context,
    get_optional_gateway_key_context,
    resolve_gateway_key_context,
)
from app.models.gateway_api_key import GatewayApiKey
from app.models.pool import Pool
from app.models.user import User
from app.schemas.gateway_key import (
    GatewayKeyGenerateRequest,
    GatewayKeyGenerateResponse,
    GatewayKeyListResponse,
    GatewayKeyRead,
    GatewayKeyVerifyRequest,
    GatewayKeyVerifyResponse,
)
from app.utils.crud import get_object_or_404
from app.core.security import mask_secret
from app.services.auth_service import hash_secret

router = APIRouter()


@router.get(
    "",
    response_model=GatewayKeyListResponse,
    summary="List gateway keys",
    description="Danh sach Gateway API Keys theo pool (chi admin).",
)
def list_gateway_keys(
    pool_id: int | None = Query(default=None),
    db: Session = Depends(db_session),
    auth: AuthContext = Depends(get_optional_auth_context),
) -> GatewayKeyListResponse:
    if auth is None or auth.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    stmt = select(GatewayApiKey).order_by(GatewayApiKey.id.desc())
    if pool_id is not None:
        stmt = stmt.where(GatewayApiKey.pool_id == pool_id)
    items = db.execute(stmt).scalars().all()
    results = [
        GatewayKeyRead(
            id=item.id,
            name=item.name,
            gateway_api_key_masked=item.key_masked,
            pool_id=item.pool_id,
            pool_name=item.pool.name if item.pool is not None else f"Pool #{item.pool_id}",
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]
    return GatewayKeyListResponse(items=results, total=len(results))


@router.post(
    "/verify",
    response_model=GatewayKeyVerifyResponse,
    summary="Verify gateway key",
    description="Kiem tra Gateway API key va tra ve thong tin pool/vendor + default model.",
)
def verify_gateway_key(
    payload: GatewayKeyVerifyRequest,
    db: Session = Depends(db_session),
) -> GatewayKeyVerifyResponse:
    context = resolve_gateway_key_context(db, payload.gateway_api_key)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway API key")

    pool = get_object_or_404(db, Pool, context.pool_id, "Pool")
    config = pool.config_json or {}
    return GatewayKeyVerifyResponse(
        gateway_api_key_masked=context.key_masked,
        gateway_key_name=context.key_name,
        vendor_id=context.vendor_id,
        vendor_name=context.vendor_name,
        vendor_code=context.vendor_code,
        pool_id=context.pool_id,
        pool_name=context.pool_name,
        pool_code=context.pool_code,
        default_model=config.get("default_model"),
    )


@router.post(
    "/generate",
    response_model=GatewayKeyGenerateResponse,
    summary="Generate gateway key",
    description="Tao Gateway API key moi cho pool (admin hoac customer).",
)
def generate_gateway_key(
    payload: GatewayKeyGenerateRequest,
    db: Session = Depends(db_session),
    auth: AuthContext | None = Depends(get_optional_auth_context),
    gateway_key: GatewayKeyContext | None = Depends(get_optional_gateway_key_context),
) -> GatewayKeyGenerateResponse:
    pool = get_object_or_404(db, Pool, payload.pool_id, "Pool")
    owner: User | None = None

    if gateway_key is not None:
        if payload.pool_id != gateway_key.pool_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gateway key cannot create another pool key")
        if gateway_key.user_id is not None:
            owner = db.get(User, gateway_key.user_id)
    else:
        if auth is None:
            user_stmt = (
                select(User)
                .where(User.pool_id == payload.pool_id, User.status == "active", User.role == "customer")
                .order_by(User.id.asc())
            )
            owner = db.execute(user_stmt).scalars().first()
            if owner is None:
                user_stmt = (
                    select(User)
                    .where(User.pool_id == payload.pool_id, User.status == "active")
                    .order_by(User.id.asc())
                )
                owner = db.execute(user_stmt).scalars().first()
        elif auth.role == "admin":
            user_stmt = select(User).where(User.pool_id == payload.pool_id, User.status == "active").order_by(User.id.asc())
            owner = db.execute(user_stmt).scalars().first()
            if owner is None and auth.user_id is not None:
                owner = db.get(User, auth.user_id)
        elif auth.role == "customer":
            owner = db.get(User, auth.user_id) if auth.user_id is not None else None
            if owner is None or owner.pool_id != payload.pool_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer user cannot create key for another pool")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or customer can generate key")

    if owner is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active customer user found for this pool")

    generated_key = f"gwk_live_{secrets.token_urlsafe(24).replace('-', 'A').replace('_', 'B')}"
    entity = GatewayApiKey(
        user_id=owner.id,
        pool_id=pool.id,
        name=payload.name,
        key_hash=hash_secret(generated_key),
        key_masked=mask_secret(generated_key),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)

    return GatewayKeyGenerateResponse(
        gateway_api_key=generated_key,
        gateway_api_key_masked=entity.key_masked,
        gateway_key_name=payload.name,
        pool_id=entity.pool_id,
        pool_name=pool.name,
    )


@router.delete(
    "/{gateway_key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete gateway key",
    description="Xoa Gateway API key (chi admin).",
)
def delete_gateway_key(
    gateway_key_id: int,
    db: Session = Depends(db_session),
    auth: AuthContext = Depends(get_optional_auth_context),
) -> None:
    if auth is None or auth.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    entity = get_object_or_404(db, GatewayApiKey, gateway_key_id, "Gateway API Key")
    db.delete(entity)
    db.commit()
