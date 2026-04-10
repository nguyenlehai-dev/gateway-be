import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Category(str, enum.Enum):
    GROK = "grok"
    FLOW = "flow"
    DREAMINA = "dreamina"


class CookieFormat(str, enum.Enum):
    TXT = "txt"
    JSON = "json"


class JobType(str, enum.Enum):
    GENERATE_IMAGE = "generate_image"
    GENERATE_VIDEO = "generate_video"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="Administrator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class Proxy(TimestampMixin, Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    protocol: Mapped[str] = mapped_column(String(16), default="http")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="proxy")


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[Category] = mapped_column(Enum(Category))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cookie_format: Mapped[CookieFormat | None] = mapped_column(Enum(CookieFormat), nullable=True)
    raw_cookie: Mapped[str | None] = mapped_column(Text, nullable=True)
    cookies: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    cache_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_data_dir: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headless: Mapped[bool] = mapped_column(Boolean, default=True)
    concurrency: Mapped[int] = mapped_column(Integer, default=1)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    screen_width: Mapped[int] = mapped_column(Integer, default=1440)
    screen_height: Mapped[int] = mapped_column(Integer, default=900)
    proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxies.id"), nullable=True)
    antidetect_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    proxy: Mapped[Proxy | None] = relationship(back_populates="profiles")
    jobs: Mapped[list["AutomationJob"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(24))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class AutomationJob(TimestampMixin, Base):
    __tablename__ = "automation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    type: Mapped[JobType] = mapped_column(Enum(JobType))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    output_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    profile: Mapped[Profile] = relationship(back_populates="jobs")
