from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ImageInput(BaseModel):
    mime_type: str = Field(..., min_length=3)
    data_base64: str = Field(..., min_length=8)


class ImageOutput(BaseModel):
    mime_type: str | None = None
    data_base64: str


class GatewayExecuteRequest(BaseModel):
    gateway_api_key: str | None = Field(default=None, min_length=10)
    api_key: str | None = Field(default=None, min_length=10)
    project_number: str | None = Field(default=None, min_length=3)
    model: str | None = Field(default=None)
    prompt: str = Field(..., min_length=1)
    input_images: list[ImageInput] = Field(default_factory=list)
    aspect_ratio: str | None = None
    image_size: str | None = None
    references_image: list[str] = Field(default_factory=list)
    references_video: list[str] = Field(default_factory=list)
    references_audios: list[str] = Field(default_factory=list)


class GatewayExecuteOutput(BaseModel):
    text: str | None = None
    images: list[ImageOutput] = Field(default_factory=list)


class GatewayUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class GatewayExecuteResponse(BaseModel):
    request_id: str
    vendor: str
    pool: str
    function: str
    model: str
    status: str
    output: GatewayExecuteOutput
    usage: GatewayUsage
    latency_ms: int


class GatewaySubmitRequest(GatewayExecuteRequest):
    webhook_url: HttpUrl | None = None
    max_attempts: int = Field(default=3, ge=1, le=5)


class GatewaySubmitResponse(BaseModel):
    request_id: str
    status: str
    function: str
    poll_path: str
    webhook_url: str | None = None


class GatewayJobStatusOutput(BaseModel):
    text: str | None = None
    images: list[ImageOutput] = Field(default_factory=list)


class GatewayJobStatusResponse(BaseModel):
    request_id: str
    function: str
    status: str
    model: str
    output: GatewayJobStatusOutput
    error_message: str | None = None
    latency_ms: int | None = None
    retry_count: int = 0
    max_attempts: int = 0
    next_retry_at: datetime | None = None
    webhook_status: str | None = None
