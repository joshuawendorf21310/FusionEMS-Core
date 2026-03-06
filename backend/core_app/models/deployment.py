from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class DeploymentState(str, Enum):
    """
    ZERO-ERROR DEPLOYMENT STATE MACHINE
    Defined in ZERO_ERROR_DIRECTIVE.md
    """
    CHECKOUT_CREATED = "CHECKOUT_CREATED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    WEBHOOK_VERIFIED = "WEBHOOK_VERIFIED"
    EVENT_RECORDED = "EVENT_RECORDED"
    AGENCY_RECORD_CREATED = "AGENCY_RECORD_CREATED"
    ADMIN_RECORD_CREATED = "ADMIN_RECORD_CREATED"
    SUBSCRIPTION_LINKED = "SUBSCRIPTION_LINKED"
    ENTITLEMENTS_ASSIGNED = "ENTITLEMENTS_ASSIGNED"
    BILLING_PHONE_PROVISIONING_PENDING = "BILLING_PHONE_PROVISIONING_PENDING"
    BILLING_PHONE_PROVISIONED = "BILLING_PHONE_PROVISIONED"
    BILLING_COMMUNICATIONS_READY = "BILLING_COMMUNICATIONS_READY"
    DEPLOYMENT_READY = "DEPLOYMENT_READY"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    LIVE = "LIVE"


class DeploymentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks a complete deployment run for an agency signup.
    Ensures visible, idempotent, and retry-safe onboarding.
    """
    __tablename__ = "deployment_runs"

    # External Event ID (e.g., Stripe Checkout Session ID)
    external_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Agency Reference
    agency_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("tenants.id"), nullable=True)

    # Current State
    current_state: Mapped[DeploymentState] = mapped_column(String(64), nullable=False, default=DeploymentState.CHECKOUT_CREATED)
    
    # Audit Trail
    steps: Mapped[list["DeploymentStep"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    failure_reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    metadata_blob: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class DeploymentStep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks individual steps within a deployment run.
    Ensures auditability and granular retry logic.
    """
    __tablename__ = "deployment_steps"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_runs.id"), nullable=False, index=True)
    run: Mapped["DeploymentRun"] = relationship(back_populates="steps")

    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # SUCCESS, FAILED, PENDING
    
    # Detailed log
    result_blob: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)


class WebhookEventLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persists every incoming webhook for audit and replay.
    Ensures zero silent failures and idempotency.
    """
    __tablename__ = "webhook_event_logs"

    source: Mapped[str] = mapped_column(String(64), nullable=False)  # STRIPE, TELNYX, OFFICE_ALLY
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)


class ProvisioningAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks external provisioning calls (Stripe API, Telnyx API).
    Ensures we don't double-bill or double-provision on retry.
    """
    __tablename__ = "provisioning_attempts"

    deployment_run_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_runs.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)  # PHONE_NUMBER, SUBSCRIPTION, USER
    external_resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)


class RetrySchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Manages safe backoff and retry for failed deployment steps.
    """
    __tablename__ = "retry_schedules"

    deployment_run_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_runs.id"), nullable=False)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    next_retry_at: Mapped[datetime] = mapped_column(nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class FailureAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    High-level explanation of failures for the Founder Dashboard/AI.
    """
    __tablename__ = "failure_audits"

    deployment_run_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("deployment_runs.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # BLOCKING, HIGH, MEDIUM
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    
    what_is_wrong: Mapped[str] = mapped_column(String(1024), nullable=False)
    why_it_matters: Mapped[str] = mapped_column(String(1024), nullable=False)
    what_to_do_next: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
