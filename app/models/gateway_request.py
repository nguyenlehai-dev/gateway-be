from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class GatewayRequest(TimestampMixin, Base):
    __tablename__ = "gateway_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("pools.id", ondelete="RESTRICT"), nullable=False, index=True)
    api_function_id: Mapped[int] = mapped_column(
        ForeignKey("api_functions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    selected_pool_api_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("pool_api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    project_number: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_masked: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    provider_request_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)

    vendor = relationship("Vendor", back_populates="gateway_requests")
    pool = relationship("Pool", back_populates="gateway_requests")
    api_function = relationship("ApiFunction", back_populates="gateway_requests")
    selected_pool_api_key = relationship("PoolApiKey", back_populates="gateway_requests")

    @property
    def selected_pool_api_key_name(self) -> str | None:
        if self.selected_pool_api_key is None:
            return None
        return self.selected_pool_api_key.name
