from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class PoolApiKey(TimestampMixin, Base):
    __tablename__ = "pool_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_api_key_masked: Mapped[str] = mapped_column(String(255), nullable=False)
    project_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")
    priority: Mapped[int] = mapped_column(nullable=False, default=100, server_default="100")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pool = relationship("Pool", back_populates="pool_api_keys")
    gateway_requests = relationship("GatewayRequest", back_populates="selected_pool_api_key")
