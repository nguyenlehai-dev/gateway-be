from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import GatewayKeyContext, require_admin, require_operator_or_gateway_key
from app.models.pool import Pool
from app.models.vendor import Vendor
from app.schemas.pool import PoolCreate, PoolListResponse, PoolRead, PoolUpdate
from app.utils.pool_config import build_pool_config, sanitize_pool_config
from app.utils.crud import ensure_unique, get_object_or_404, paginate
from app.utils.validators import validate_status

router = APIRouter()


@router.get(
    "",
    response_model=PoolListResponse,
    summary="List pools",
    description="Danh sach pool theo vendor, ho tro search va filter status.",
)
def list_pools(
    vendor_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> PoolListResponse:
    validate_status(status_filter)
    stmt = select(Pool).order_by(Pool.id.desc())
    if isinstance(access, GatewayKeyContext):
        stmt = stmt.where(Pool.id == access.pool_id)
    if vendor_id is not None:
        stmt = stmt.where(Pool.vendor_id == vendor_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Pool.name.ilike(pattern), Pool.slug.ilike(pattern), Pool.code.ilike(pattern)))
    if status_filter:
        stmt = stmt.where(Pool.status == status_filter)

    items, total = paginate(stmt, db, offset, limit)
    for item in items:
        item.config_json = sanitize_pool_config(item.config_json)
    return PoolListResponse(items=items, total=total)


@router.post("", response_model=PoolRead, status_code=status.HTTP_201_CREATED)
def create_pool(payload: PoolCreate, db: Session = Depends(db_session), _: object = Depends(require_admin)) -> PoolRead:
    validate_status(payload.status)
    get_object_or_404(db, Vendor, payload.vendor_id, "Vendor")
    ensure_unique(db, Pool, "slug", payload.slug, "Pool slug already exists")
    duplicate = db.execute(
        select(Pool).where(and_(Pool.vendor_id == payload.vendor_id, Pool.code == payload.code))
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pool code already exists in this vendor")

    data = payload.model_dump()
    data["config_json"] = build_pool_config(
        timeout_seconds=data.get("config_json", {}).get("timeout_seconds") if data.get("config_json") else None,
        provider=data.get("config_json", {}).get("provider") if data.get("config_json") else None,
        default_model=payload.default_model,
        existing_config=data.get("config_json"),
    )
    for transient_key in ("default_model",):
        data.pop(transient_key, None)
    pool = Pool(**data)
    db.add(pool)
    db.commit()
    db.refresh(pool)
    pool.config_json = sanitize_pool_config(pool.config_json)
    return pool


@router.get(
    "/{pool_id}",
    response_model=PoolRead,
    summary="Get pool",
    description="Chi tiet pool (config duoc sanitize).",
)
def get_pool(
    pool_id: int,
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> PoolRead:
    if isinstance(access, GatewayKeyContext) and pool_id != access.pool_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    pool = get_object_or_404(db, Pool, pool_id, "Pool")
    pool.config_json = sanitize_pool_config(pool.config_json)
    return pool


@router.put("/{pool_id}", response_model=PoolRead)
@router.patch("/{pool_id}", response_model=PoolRead)
def update_pool(
    pool_id: int,
    payload: PoolUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> PoolRead:
    pool = get_object_or_404(db, Pool, pool_id, "Pool")
    data = payload.model_dump(exclude_unset=True)
    validate_status(data.get("status"))

    target_vendor_id = data.get("vendor_id", pool.vendor_id)
    if "vendor_id" in data:
        get_object_or_404(db, Vendor, target_vendor_id, "Vendor")
    if "slug" in data:
        ensure_unique(db, Pool, "slug", data["slug"], "Pool slug already exists", exclude_id=pool_id)
    if "code" in data:
        duplicate = db.execute(
            select(Pool).where(and_(Pool.vendor_id == target_vendor_id, Pool.code == data["code"], Pool.id != pool_id))
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pool code already exists in this vendor")

    if any(
        key in payload.model_fields_set
        for key in {
            "config_json",
            "default_model",
        }
    ):
        data["config_json"] = build_pool_config(
            timeout_seconds=data.get("config_json", {}).get("timeout_seconds") if data.get("config_json") else None,
            provider=data.get("config_json", {}).get("provider") if data.get("config_json") else None,
            default_model=payload.default_model,
            existing_config=pool.config_json,
        )
    for transient_key in ("default_model",):
        data.pop(transient_key, None)

    for key, value in data.items():
        setattr(pool, key, value)

    db.commit()
    db.refresh(pool)
    pool.config_json = sanitize_pool_config(pool.config_json)
    return pool


@router.delete("/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool(pool_id: int, db: Session = Depends(db_session), _: object = Depends(require_admin)) -> None:
    pool = get_object_or_404(db, Pool, pool_id, "Pool")
    if pool.gateway_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pool cannot be deleted because it already has gateway requests",
        )
    db.delete(pool)
    db.commit()
