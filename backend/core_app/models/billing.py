from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ClaimState(str, Enum):
    """
    CLAIM STATE MACHINE
    Defined in ZERO_ERROR_DIRECTIVE.md
    """
    DRAFT = "DRAFT"
    READY_FOR_BILLING_REVIEW = "READY_FOR_BILLING_REVIEW"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DENIED = "DENIED"
    PAID = "PAID"
    PARTIAL_PAID = "PARTIAL_PAID"
    APPEAL_DRAFTED = "APPEAL_DRAFTED"
    APPEAL_PENDING_REVIEW = "APPEAL_PENDING_REVIEW"
    CORRECTED_CLAIM_PENDING = "CORRECTED_CLAIM_PENDING"
    CLOSED = "CLOSED"


class PatientBalanceState(str, Enum):
    """
    PATIENT BALANCE STATE MACHINE
    Defined in ZERO_ERROR_DIRECTIVE.md
    """
    INSURANCE_PENDING = "INSURANCE_PENDING"
    SECONDARY_PENDING = "SECONDARY_PENDING"
    PATIENT_BALANCE_OPEN = "PATIENT_BALANCE_OPEN"
    PATIENT_AUTOPAY_PENDING = "PATIENT_AUTOPAY_PENDING"
    PAYMENT_PLAN_ACTIVE = "PAYMENT_PLAN_ACTIVE"
    DENIAL_UNDER_REVIEW = "DENIAL_UNDER_REVIEW"
    APPEAL_IN_PROGRESS = "APPEAL_IN_PROGRESS"
    COLLECTIONS_READY = "COLLECTIONS_READY"
    SENT_TO_COLLECTIONS = "SENT_TO_COLLECTIONS"
    STATE_DEBT_SETOFF_READY = "STATE_DEBT_SETOFF_READY"
    STATE_DEBT_SETOFF_SUBMITTED = "STATE_DEBT_SETOFF_SUBMITTED"
    WRITTEN_OFF = "WRITTEN_OFF"
    BAD_DEBT_CLOSED = "BAD_DEBT_CLOSED"


class Claim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Core Billing entity. Represents an ePCR converted to a billable event.
    """
    __tablename__ = "claims"

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), unique=True, nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    # State Machine
    status: Mapped[ClaimState] = mapped_column(String(32), default=ClaimState.DRAFT, nullable=False, index=True)
    patient_balance_status: Mapped[PatientBalanceState] = mapped_column(String(32), default=PatientBalanceState.INSURANCE_PENDING, nullable=False)
    
    # Financials
    total_billed_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    insurance_paid_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Required Data Tracking per Directive
    primary_adjustment_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    secondary_expected_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    secondary_paid_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    patient_responsibility_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    patient_paid_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    remaining_collectible_balance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    writeoff_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Legacy fields
    adjustment_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_due_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Workflow Tracking
    collections_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    aging_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_patient_contact_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    autopay_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payment_link_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    appeal_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Payer Info
    primary_payer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # Office Ally Payer ID
    primary_payer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Validation
    validation_errors: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_valid: Mapped[bool] = mapped_column(default=False, nullable=False)


class ClaimIssue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks specific issues with a claim (e.g. Missing SSN, Coding Error).
    Includes AI Explanation.
    """
    __tablename__ = "claim_issues"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False) # BLOCKING, HIGH...
    source: Mapped[str] = mapped_column(String(32), nullable=False) # RULE, AI
    
    what_is_wrong: Mapped[str] = mapped_column(String(1024), nullable=False)
    why_it_matters: Mapped[str] = mapped_column(String(1024), nullable=False)
    what_to_do_next: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)


class PatientBalanceLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Ledger for patient responsibility tracking.
    """
    __tablename__ = "patient_balance_ledger"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False) # CHARGE, PAYMENT, ADJ
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)


class PaymentLinkEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks Stripe Payment Links sent to patients.
    """
    __tablename__ = "payment_link_events"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    stripe_payment_link_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False) # SENT, PAID, EXPIRED
    sent_via: Mapped[str] = mapped_column(String(16), default="SMS", nullable=False) # SMS, EMAIL, MAIL


class CollectionsReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Review process before sending to collections.
    """
    __tablename__ = "collections_reviews"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    reviewed_by_user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    reason_for_hold: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decision_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class ClaimAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Audit trail for claim lifecycle changes.
    """
    __tablename__ = "claim_audit_events"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # or system service
    
    event_type: Mapped[str] = mapped_column(String(64), nullable=False) # STATUS_CHANGE, SUBMISSION, PAYMENT, DENIAL
    old_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_blob: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ReminderEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks billing reminders sent to patients.
    """
    __tablename__ = "reminder_events"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    
    reminder_type: Mapped[str] = mapped_column(String(32), default="SMS_BALANCE", nullable=False) # SMS, EMAIL, CALL
    sent_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False) # DELIVERED, FAILED, CLICKED


class AppealReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Track internal review process for an appeal.
    """
    __tablename__ = "appeal_reviews"

    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    denial_code: Mapped[str] = mapped_column(String(32), nullable=False)
    
    ai_recommended_strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_biller_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # PENDING, APPROVED_FOR_SUBMISSION, REJECTED
    draft_appeal_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class HumanApprovalEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Generic approval event for high-risk actions (Refunds, Adjustments, Write-offs).
    """
    __tablename__ = "human_approval_events"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    action_type: Mapped[str] = mapped_column(String(64), nullable=False) # WRITE_OFF, REFUND, COLLECTIONS_STOP
    approved_by_user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    justification: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
