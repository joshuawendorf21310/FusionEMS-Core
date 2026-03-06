from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AgencyPhoneNumber(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Telnyx Phone Number assigned to an agency for Billing Comms.
    Strictly billing-only.
    """
    __tablename__ = "agency_phone_numbers"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False) # e.g. +19195551234
    telnyx_phone_number_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    
    # Configuration
    voice_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    fax_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False) # ACTIVE, RELEASED, PENDING


class CommunicationThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Siloed conversation thread (Billing Support, Patient Payment).
    Auditable and viewable in dashboard.
    """
    __tablename__ = "communication_threads"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("patients.id"), nullable=True)
    
    channel: Mapped[str] = mapped_column(String(16), default="SMS", nullable=False) # SMS, EMAIL, VOICE
    topic: Mapped[str] = mapped_column(String(32), default="BILLING_GENERAL", nullable=False) # PATIENT_BALANCE, BILLING_SUPPORT
    
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False) # OPEN, CLOSED, ESCALATED_TO_HUMAN
    latest_message_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)


class CommunicationMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual message in a thread.
    """
    __tablename__ = "communication_messages"

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("communication_threads.id"), nullable=False, index=True)
    
    direction: Mapped[str] = mapped_column(String(16), nullable=False) # INBOUND, OUTBOUND
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    sender_type: Mapped[str] = mapped_column(String(16), default="SYSTEM", nullable=False) # SYSTEM, AI, HUMAN, PATIENT
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    telnyx_message_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="SENT", nullable=False) # QUEUED, SENT, DELIVERED, FAILED


class MailFulfillmentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Physical mail sent via Lob (e.g. Statements, Notices).
    """
    __tablename__ = "mail_fulfillment_records"

    claim_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("claims.id"), nullable=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    lob_letter_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False) # e.g. "STATEMENT_V1"
    
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False) # CREATED, MAILED, IN_TRANSIT, DELIVERED, RETURNED
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
