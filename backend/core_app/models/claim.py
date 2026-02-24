import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class PayerType(str, enum.Enum):
    MEDICARE = "MEDICARE"
    MEDICAID = "MEDICAID"
    COMMERCIAL = "COMMERCIAL"
    SELFPAY = "SELFPAY"
    OTHER = "OTHER"


class ClaimServiceLevel(str, enum.Enum):
    BLS = "BLS"
    ALS1 = "ALS1"
    ALS2 = "ALS2"
    SCT = "SCT"
    CCT = "CCT"
    OTHER = "OTHER"


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    READY_TO_EXPORT = "ready_to_export"
    EXPORTED = "exported"
    SUBMITTED = "submitted"
    PAID = "paid"
    DENIED = "denied"
    APPEAL_NEEDED = "appeal_needed"
    CLOSED = "closed"


ALLOWED_CLAIM_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.PENDING_REVIEW},
    ClaimStatus.PENDING_REVIEW: {ClaimStatus.READY_TO_EXPORT},
    ClaimStatus.READY_TO_EXPORT: {ClaimStatus.EXPORTED},
    ClaimStatus.EXPORTED: {ClaimStatus.SUBMITTED},
    ClaimStatus.SUBMITTED: {ClaimStatus.PAID, ClaimStatus.DENIED},
    ClaimStatus.DENIED: {ClaimStatus.APPEAL_NEEDED, ClaimStatus.CLOSED},
    ClaimStatus.APPEAL_NEEDED: {ClaimStatus.CLOSED},
    ClaimStatus.PAID: {ClaimStatus.CLOSED},
    ClaimStatus.CLOSED: set(),
}


class Claim(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "claims"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    payer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    payer_type: Mapped[PayerType] = mapped_column(Enum(PayerType, name="claim_payer_type"), nullable=False)
    icd10_primary: Mapped[str] = mapped_column(String(16), nullable=False)
    icd10_secondary_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    modifiers_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    service_level: Mapped[ClaimServiceLevel] = mapped_column(Enum(ClaimServiceLevel, name="claim_service_level"), nullable=False)
    transport_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    origin_zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    destination_zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mileage_loaded: Mapped[float | None] = mapped_column(nullable=True)
    charge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    patient_responsibility_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, name="claim_status"), nullable=False, default=ClaimStatus.DRAFT)
    denial_reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    denial_reason_text_redacted_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def allowed_claim_transition_targets(from_status: ClaimStatus) -> set[ClaimStatus]:
    return ALLOWED_CLAIM_TRANSITIONS.get(from_status, set())
