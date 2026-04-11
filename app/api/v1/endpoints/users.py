from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import require_admin
from app.models.pool import Pool
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserRead, UserUpdate
from app.services.auth_service import hash_password
from app.utils.crud import get_object_or_404, paginate

router = APIRouter()


def _ensure_unique_user(db: Session, *, username: str | None = None, email: str | None = None, exclude_id: int | None = None) -> None:
    if username:
        stmt = select(User).where(User.username == username.strip())
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        if db.execute(stmt).scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if email:
        stmt = select(User).where(User.email == email.strip())
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        if db.execute(stmt).scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")


@router.get("", response_model=UserListResponse)
def list_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> UserListResponse:
    stmt = select(User).order_by(User.id.desc())
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(User.username.ilike(pattern), User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if role:
        stmt = stmt.where(User.role == role)
    if pool_id is not None:
        stmt = stmt.where(User.pool_id == pool_id)
    items, total = paginate(stmt, db, offset, limit)
    return UserListResponse(items=items, total=total)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(db_session), _: object = Depends(require_admin)) -> UserRead:
    _ensure_unique_user(db, username=payload.username, email=payload.email)
    if payload.pool_id is not None:
        get_object_or_404(db, Pool, payload.pool_id, "Pool")
    entity = User(
        username=payload.username.strip(),
        email=payload.email.strip() if payload.email else None,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=payload.status,
        pool_id=payload.pool_id,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.patch("/{user_id}", response_model=UserRead)
@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> UserRead:
    entity = get_object_or_404(db, User, user_id, "User")
    if payload.email is not None or payload.full_name is not None or payload.password is not None or payload.role is not None or payload.pool_id is not None:
        _ensure_unique_user(db, email=payload.email, exclude_id=user_id)
    if payload.pool_id is not None:
        get_object_or_404(db, Pool, payload.pool_id, "Pool")

    if payload.email is not None:
        entity.email = payload.email.strip() if payload.email else None
    if payload.full_name is not None:
        entity.full_name = payload.full_name.strip()
    if payload.password is not None:
        entity.password_hash = hash_password(payload.password)
    if payload.role is not None:
        entity.role = payload.role
    if payload.status is not None:
        entity.status = payload.status
    if payload.pool_id is not None:
        entity.pool_id = payload.pool_id

    db.commit()
    db.refresh(entity)
    return entity
