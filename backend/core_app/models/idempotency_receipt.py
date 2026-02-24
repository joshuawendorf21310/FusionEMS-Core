from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class IdempotencyReceipt(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "idempotency_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", "route_key", name="uq_idempotency_tenant_key_route"),
    )

    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    route_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
