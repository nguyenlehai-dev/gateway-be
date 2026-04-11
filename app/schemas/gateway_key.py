from datetime import datetime

from pydantic import BaseModel, Field


class GatewayKeyVerifyRequest(BaseModel):
    gateway_api_key: str = Field(..., min_length=10)


class GatewayKeyGenerateRequest(BaseModel):
    pool_id: int
    name: str = Field(..., min_length=1, max_length=120)


class GatewayKeyVerifyResponse(BaseModel):
    gateway_api_key_masked: str
    gateway_key_name: str | None = None
    vendor_id: int
    vendor_name: str
    vendor_code: str
    pool_id: int
    pool_name: str
    pool_code: str
    default_model: str | None = None


class GatewayKeyGenerateResponse(BaseModel):
    gateway_api_key: str
    gateway_api_key_masked: str
    gateway_key_name: str
    pool_id: int
    pool_name: str


class GatewayKeyRead(BaseModel):
    id: int
    name: str
    gateway_api_key_masked: str
    pool_id: int
    pool_name: str
    status: str
    created_at: datetime
    updated_at: datetime


class GatewayKeyListResponse(BaseModel):
    items: list[GatewayKeyRead]
    total: int
