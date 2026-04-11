from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PoolApiKeyBase(BaseModel):
    pool_id: int
    name: str = Field(..., min_length=1, max_length=120)
    provider_api_key: str | None = Field(default=None, min_length=10, exclude=True)
    project_number: str = Field(..., min_length=3, max_length=100)
    status: str = "active"
    priority: int = 100


class PoolApiKeyCreate(PoolApiKeyBase):
    provider_api_key: str = Field(..., min_length=10)


class PoolApiKeyUpdate(BaseModel):
    pool_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider_api_key: str | None = Field(default=None, min_length=10, exclude=True)
    project_number: str | None = Field(default=None, min_length=3, max_length=100)
    status: str | None = None
    priority: int | None = None


class PoolApiKeyRead(BaseModel):
    id: int
    pool_id: int
    name: str
    provider_api_key_masked: str
    project_number: str
    status: str
    priority: int
    last_used_at: datetime | None = None
    last_error_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PoolApiKeyListResponse(BaseModel):
    items: list[PoolApiKeyRead]
    total: int
