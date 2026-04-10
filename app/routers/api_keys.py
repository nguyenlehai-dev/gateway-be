from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyRead
from app.utils.security import api_key_prefix, generate_api_key, hash_api_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(db: Session = Depends(get_db)) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all())


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db)) -> ApiKeyCreateResponse:
    raw_key = generate_api_key()
    record = ApiKey(
        **payload.model_dump(),
        key_prefix=api_key_prefix(raw_key),
        key_hash=hash_api_key(raw_key),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiKeyCreateResponse(api_key=record, raw_key=raw_key)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(api_key_id: int, db: Session = Depends(get_db)) -> None:
    record = db.get(ApiKey, api_key_id)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(record)
    db.commit()
