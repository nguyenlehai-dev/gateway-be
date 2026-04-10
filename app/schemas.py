from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Category, CookieFormat, JobStatus, JobType


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ProxyBase(BaseModel):
    name: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: str = "http"
    is_active: bool = True
    notes: str | None = None


class ProxyCreate(ProxyBase):
    pass


class ProxyRead(ProxyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProfileBase(BaseModel):
    name: str
    category: Category
    description: str | None = None
    cache_path: str | None = None
    user_data_dir: str | None = None
    headless: bool = True
    concurrency: int = Field(default=1, ge=1, le=20)
    timezone: str | None = None
    locale: str | None = None
    user_agent: str | None = None
    screen_width: int = 1440
    screen_height: int = 900
    proxy_id: int | None = None
    antidetect_config: dict | None = None
    is_active: bool = True


class ProfileCreate(ProfileBase):
    cookie_format: CookieFormat | None = None
    raw_cookie: str | None = None
    cookies: list[dict] | None = None


class ProfileUpdate(BaseModel):
    description: str | None = None
    headless: bool | None = None
    concurrency: int | None = Field(default=None, ge=1, le=20)
    timezone: str | None = None
    locale: str | None = None
    user_agent: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    proxy_id: int | None = None
    antidetect_config: dict | None = None
    is_active: bool | None = None


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cookie_format: CookieFormat | None = None
    raw_cookie: str | None = None
    cookies: list[dict] | None = None
    created_at: datetime
    updated_at: datetime


class CookieImportResponse(BaseModel):
    profile_id: int
    cookie_format: CookieFormat
    cookie_count: int


class ApiKeyBase(BaseModel):
    name: str
    description: str | None = None
    rate_limit_per_minute: int = 60
    is_active: bool = True


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyRead(ApiKeyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    api_key: ApiKeyRead
    raw_key: str


class AutomationJobCreate(BaseModel):
    profile_id: int
    type: JobType
    prompt: str
    metadata_json: dict | None = None


class AutomationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    profile_id: int
    type: JobType
    prompt: str
    status: JobStatus
    output_url: str | None
    error_message: str | None
    metadata_json: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationPreview(BaseModel):
    provider: Category
    headless: bool
    concurrency: int
    launch_options: dict
    steps: list[str]


class DashboardStats(BaseModel):
    profiles: int
    active_profiles: int
    proxies: int
    active_api_keys: int
    queued_jobs: int
    running_jobs: int
