from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import AuthContext, get_auth_context
from app.models.pool import Pool
from app.models.user import User
from app.schemas.customer_auth import CustomerSignupRequest, CustomerSignupResponse
from app.schemas.auth import AuthUserRead, LoginRequest, LoginResponse
from app.services.auth_service import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> LoginResponse:
    user = db.execute(select(User).where(User.username == payload.username.strip())).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    access_token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        pool_id=user.pool_id,
    )
    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=AuthUserRead.model_validate(user),
    )


@router.get("/customer-pools")
def customer_pools(db: Session = Depends(db_session)) -> list[dict[str, int | str]]:
    pools = db.execute(select(Pool).where(Pool.status == "active").order_by(Pool.name.asc())).scalars().all()
    return [{"id": pool.id, "name": pool.name, "code": pool.code} for pool in pools]


@router.post("/customer-signup", response_model=CustomerSignupResponse, status_code=status.HTTP_201_CREATED)
def customer_signup(payload: CustomerSignupRequest, db: Session = Depends(db_session)) -> CustomerSignupResponse:
    if db.execute(select(User).where(User.username == payload.username.strip())).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if payload.email and db.execute(select(User).where(User.email == payload.email.strip())).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    pool = db.get(Pool, payload.pool_id)
    if pool is None or pool.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    user = User(
        username=payload.username.strip(),
        email=payload.email.strip() if payload.email else None,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role="customer",
        status="active",
        pool_id=payload.pool_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return CustomerSignupResponse(user=AuthUserRead.model_validate(user))


@router.get("/me", response_model=AuthUserRead)
def me(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(db_session)) -> AuthUserRead:
    if auth.user_id is None:
        return AuthUserRead(
            id=0,
            username="system",
            email=None,
            full_name="System Access",
            role=auth.role,
            status="active",
            pool_id=auth.pool_id,
        )

    user = db.get(User, auth.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthUserRead.model_validate(user)
