from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class StateDebtSetoffProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Platform-level configuration for a specific State's Debt Setoff Program.
    Enabled globally by platform admin, enrolled individually by agencies.
    """
    __tablename__ = "state_debt_setoff_profiles"

    state_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False) # e.g. "NC"
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Eligibility Rules
    min_debt_amount_cents: Mapped[int] = mapped_column(default=5000, nullable=False)
    min_days_delinquent: Mapped[int] = mapped_column(default=60, nullable=False)
    eligible_agency_types: Mapped[list[str]] = mapped_column(JSONB, default=["MUNICIPALITY", "COUNTY", "HOSPITAL_DISTRICT"], nullable=False)
    
    # Process
    export_format: Mapped[str] = mapped_column(String(64), default="CSV_STANDARD", nullable=False)
    submission_frequency: Mapped[str] = mapped_column(String(32), default="ANNUAL", nullable=False)
    
    active: Mapped[bool] = mapped_column(default=False, nullable=False)


class AgencyDebtSetoffEnrollment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks an agency's enrollment in the state program.
    """
    __tablename__ = "agency_debt_setoff_enrollments"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    state_profile_id: Mapped[UUID] = mapped_column(ForeignKey("state_debt_setoff_profiles.id"), nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # PENDING, ACTIVE, SUSPENDED
    enrollment_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    tax_id_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    agreement_signed: Mapped[bool] = mapped_column(default=False, nullable=False)


class DebtSetoffSubmissionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual debt item submitted to the state.
    """
    __tablename__ = "debt_setoff_submissions"

    enrollment_id: Mapped[UUID] = mapped_column(ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False) # Assuming patients table exists
    claim_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # Linked claim causing debt
    
    amount_submitted_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    submission_batch_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", nullable=False) # SUBMITTED, REJECTED, ACCEPTED, PAID, REVERSED
    

class DebtSetoffResponseRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Response/Update from the state regarding a submission (e.g. Offset Success).
    """
    __tablename__ = "debt_setoff_responses"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("debt_setoff_submissions.id"), nullable=False)
    
    response_code: Mapped[str] = mapped_column(String(64), nullable=True)
    amount_offset_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
