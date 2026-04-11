from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ApiFunction(TimestampMixin, Base):
    __tablename__ = "api_functions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str] = mapped_column(String(20), nullable=False, default="POST", server_default="POST")
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_action: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    pool = relationship("Pool", back_populates="api_functions")
    gateway_requests = relationship("GatewayRequest", back_populates="api_function")
