import enum

from sqlalchemy import Boolean, Enum, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class AiRunType(str, enum.Enum):
    BILLING_ANALYSIS = "BILLING_ANALYSIS"
    ICD10_SUGGESTION = "ICD10_SUGGESTION"
    MODIFIER_SUGGESTION = "MODIFIER_SUGGESTION"
    DENIAL_RISK = "DENIAL_RISK"
    APPEAL_DRAFT = "APPEAL_DRAFT"
    TRANSCRIPT_SUMMARY = "TRANSCRIPT_SUMMARY"


class AiRun(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ai_runs"

    run_type: Mapped[AiRunType] = mapped_column(Enum(AiRunType, name="ai_run_type"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AiPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "ai_policies"

    allow_features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requires_human_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
