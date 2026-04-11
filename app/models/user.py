from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="operator", server_default="operator")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")
    pool_id: Mapped[int | None] = mapped_column(ForeignKey("pools.id", ondelete="SET NULL"), nullable=True, index=True)

    pool = relationship("Pool")
    gateway_api_keys = relationship("GatewayApiKey", back_populates="user", cascade="all, delete-orphan")
