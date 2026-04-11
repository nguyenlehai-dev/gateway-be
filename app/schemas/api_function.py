from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiFunctionBase(BaseModel):
    pool_id: int
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    http_method: str = "POST"
    path: str | None = None
    provider_action: str = Field(..., min_length=1, max_length=255)
    status: str = "active"
    schema_definition: dict | None = Field(default=None, validation_alias="schema_json", serialization_alias="schema_json")


class ApiFunctionCreate(ApiFunctionBase):
    pass


class ApiFunctionUpdate(BaseModel):
    pool_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    http_method: str | None = None
    path: str | None = None
    provider_action: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = None
    schema_definition: dict | None = Field(default=None, validation_alias="schema_json", serialization_alias="schema_json")


class ApiFunctionRead(ApiFunctionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiFunctionListResponse(BaseModel):
    items: list[ApiFunctionRead]
    total: int
