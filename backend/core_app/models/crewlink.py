from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AlertState(str, Enum):
    """
    CREWLINK ALERT STATE MACHINE
    Defined in ZERO_ERROR_DIRECTIVE.md
    """
    CREATED = "CREATED"
    DISPATCHED = "DISPATCHED" # Sent to devices
    ACKNOWLEDGED = "ACKNOWLEDGED" # At least one crew acknowledged
    ACCEPTED = "ACCEPTED" # Crew accepted mission
    DECLINED = "DECLINED" # Crew declined mission
    ESCALATED = "ESCALATED" # Time out, sent to next group
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class CrewPagingAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Operational Paging Alert (e.g., "Code 3 Response").
    Separate from Billing SMS. Uses Firebase/Native Push.
    """
    __tablename__ = "crew_paging_alerts"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    
    # Priority
    priority: Mapped[str] = mapped_column(String(16), default="ROUTINE", nullable=False) # EMERGENT, URGENT, ROUTINE
    
    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # State
    status: Mapped[AlertState] = mapped_column(String(32), default=AlertState.CREATED, nullable=False)
    dispatched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class CrewPushDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Registered mobile device for a crew member.
    """
    __tablename__ = "crew_push_devices"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False) # Linked to Users table
    device_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # FCM Token or APNS
    platform: Mapped[str] = mapped_column(String(16), default="ANDROID", nullable=False) # IOS, ANDROID
    
    last_active_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CrewPagingRecipient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual crew member targeted by an alert.
    """
    __tablename__ = "crew_paging_recipients"

    alert_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_alerts.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("crew_push_devices.id"), nullable=True) # Specific device used if known

    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False) # SENT, DELIVERED, READ, ACKNOWLEDGED, ACCEPTED, DECLINED
    response_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class CrewMissionAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Active mission context for a crew.
    """
    __tablename__ = "crew_mission_assignments"

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), unique=True, nullable=False)
    
    assigned_crew_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False) # List of user IDs
    mission_status: Mapped[str] = mapped_column(String(32), default="ASSIGNED", nullable=False) # ASSIGNED, EN_ROUTE, ON_SCENE, TRANSPORTING, AT_DESTINATION, CLEAR
    
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
