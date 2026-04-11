from pydantic import BaseModel

from app.schemas.auth import AuthUserRead


class CustomerSignupRequest(BaseModel):
    username: str
    email: str | None = None
    full_name: str
    password: str
    pool_id: int


class CustomerSignupResponse(BaseModel):
    user: AuthUserRead
