from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GatewayRequestRead(BaseModel):
    id: int
    vendor_id: int
    pool_id: int
    api_function_id: int
    selected_pool_api_key_id: int | None = None
    selected_pool_api_key_name: str | None = None
    request_id: str
    model: str
    project_number: str
    api_key_masked: str
    payload_json: dict
    provider_request_json: dict | None = None
    provider_response_json: dict | None = None
    output_text: str | None = None
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GatewayRequestListResponse(BaseModel):
    items: list[GatewayRequestRead]
    total: int


class GatewayRequestStatusRead(BaseModel):
    request_id: str
    status: str
    model: str
    output_text: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
