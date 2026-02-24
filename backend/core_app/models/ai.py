import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class AiRun(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_runs"

    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AiPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_policies"

    allow_billing_analysis: Mapped[bool] = mapped_column(nullable=False, default=True)
    allow_icd10_suggestions: Mapped[bool] = mapped_column(nullable=False, default=True)
    requires_human_confirmation: Mapped[bool] = mapped_column(nullable=False, default=True)
