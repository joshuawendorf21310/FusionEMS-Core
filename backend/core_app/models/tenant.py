import uuid

from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenants"

    tenant_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    billing_tier: Mapped[str] = mapped_column(String(64), nullable=False, default='starter')
    modules_enabled: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False, default='inactive')
    accreditation_status: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    compliance_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    feature_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TenantScopedMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
