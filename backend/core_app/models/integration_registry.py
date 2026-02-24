import enum

from sqlalchemy import Boolean, Enum, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class IntegrationProvider(str, enum.Enum):
    STRIPE = "STRIPE"
    TELNYX = "TELNYX"
    WEATHER = "WEATHER"
    REDIS = "REDIS"
    SES = "SES"
    OPENAI = "OPENAI"
    OTHER = "OTHER"


class IntegrationRegistry(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "integration_registry"
    __table_args__ = (UniqueConstraint("tenant_id", "provider_name", name="uq_integration_registry_tenant_provider"),)

    provider_name: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider"), nullable=False
    )
    enabled_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    config_encrypted_data_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    config_key_id: Mapped[str] = mapped_column(String(256), nullable=False)
    config_nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    config_kms_encryption_context_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
