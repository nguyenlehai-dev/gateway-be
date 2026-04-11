from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def get_object_or_404(db: Session, model, object_id: int, label: str):
    instance = db.get(model, object_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return instance


def ensure_unique(db: Session, model, field_name: str, value, detail: str, exclude_id: int | None = None) -> None:
    stmt = select(model).where(getattr(model, field_name) == value)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def paginate(select_stmt, db: Session, offset: int, limit: int):
    total = db.execute(select(func.count()).select_from(select_stmt.order_by(None).subquery())).scalar_one()
    items = db.execute(select_stmt.offset(offset).limit(limit)).scalars().all()
    return items, total
