from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import require_admin
from app.core.security import mask_secret
from app.models.pool import Pool
from app.models.pool_api_key import PoolApiKey
from app.schemas.pool_api_key import PoolApiKeyCreate, PoolApiKeyListResponse, PoolApiKeyRead, PoolApiKeyUpdate
from app.utils.crud import get_object_or_404, paginate
from app.utils.validators import validate_status

router = APIRouter()


@router.get("", response_model=PoolApiKeyListResponse)
def list_pool_api_keys(
    pool_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> PoolApiKeyListResponse:
    validate_status(status_filter)
    stmt = select(PoolApiKey).order_by(PoolApiKey.priority.asc(), PoolApiKey.id.asc())
    if pool_id is not None:
        stmt = stmt.where(PoolApiKey.pool_id == pool_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(PoolApiKey.name.ilike(pattern), PoolApiKey.project_number.ilike(pattern)))
    if status_filter:
        stmt = stmt.where(PoolApiKey.status == status_filter)
    items, total = paginate(stmt, db, offset, limit)
    return PoolApiKeyListResponse(items=items, total=total)


@router.post("", response_model=PoolApiKeyRead, status_code=status.HTTP_201_CREATED)
def create_pool_api_key(
    payload: PoolApiKeyCreate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> PoolApiKeyRead:
    validate_status(payload.status)
    get_object_or_404(db, Pool, payload.pool_id, "Pool")
    duplicate = db.execute(
        select(PoolApiKey).where(and_(PoolApiKey.pool_id == payload.pool_id, PoolApiKey.name == payload.name))
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="API key name already exists in this pool")

    entity = PoolApiKey(
        pool_id=payload.pool_id,
        name=payload.name,
        provider_api_key=payload.provider_api_key.strip(),
        provider_api_key_masked=mask_secret(payload.provider_api_key.strip()),
        project_number=payload.project_number.strip(),
        status=payload.status,
        priority=payload.priority,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("/{api_key_id}", response_model=PoolApiKeyRead)
def get_pool_api_key(
    api_key_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> PoolApiKeyRead:
    return get_object_or_404(db, PoolApiKey, api_key_id, "Pool API Key")


@router.patch("/{api_key_id}", response_model=PoolApiKeyRead)
@router.put("/{api_key_id}", response_model=PoolApiKeyRead)
def update_pool_api_key(
    api_key_id: int,
    payload: PoolApiKeyUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> PoolApiKeyRead:
    entity = get_object_or_404(db, PoolApiKey, api_key_id, "Pool API Key")
    data = payload.model_dump(exclude_unset=True)
    validate_status(data.get("status"))

    target_pool_id = data.get("pool_id", entity.pool_id)
    if "pool_id" in data:
        get_object_or_404(db, Pool, target_pool_id, "Pool")
    if "name" in data:
        duplicate = db.execute(
            select(PoolApiKey).where(
                and_(PoolApiKey.pool_id == target_pool_id, PoolApiKey.name == data["name"], PoolApiKey.id != api_key_id)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="API key name already exists in this pool")

    if "provider_api_key" in data and data["provider_api_key"]:
        stripped_key = data["provider_api_key"].strip()
        data["provider_api_key"] = stripped_key
        data["provider_api_key_masked"] = mask_secret(stripped_key)

    if "project_number" in data and data["project_number"] is not None:
        data["project_number"] = data["project_number"].strip()

    for key, value in data.items():
        setattr(entity, key, value)

    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool_api_key(
    api_key_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> None:
    entity = get_object_or_404(db, PoolApiKey, api_key_id, "Pool API Key")
    db.delete(entity)
    db.commit()
