from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Pool(TimestampMixin, Base):
    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    vendor = relationship("Vendor", back_populates="pools")
    api_functions = relationship("ApiFunction", back_populates="pool", cascade="all, delete-orphan")
    pool_api_keys = relationship("PoolApiKey", back_populates="pool", cascade="all, delete-orphan")
    gateway_requests = relationship("GatewayRequest", back_populates="pool")
    users = relationship("User", back_populates="pool")
