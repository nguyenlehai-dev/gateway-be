from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PoolBase(BaseModel):
    vendor_id: int
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    status: str = "active"
    config_json: dict | None = None
    default_model: str | None = Field(default=None, min_length=3, exclude=True)


class PoolCreate(PoolBase):
    pass


class PoolUpdate(BaseModel):
    vendor_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: str | None = None
    config_json: dict | None = None
    default_model: str | None = Field(default=None, min_length=3, exclude=True)


class PoolRead(PoolBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PoolListResponse(BaseModel):
    items: list[PoolRead]
    total: int
