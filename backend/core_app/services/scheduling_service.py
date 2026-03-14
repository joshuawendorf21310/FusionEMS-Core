"""Scheduling service for Phase 6 & 7 (CrewLink & Scheduling).

Handles shift assignment with credential enforcement and Karolinska Sleepiness
Scale (KSS) fatigue logging.  All operations are strictly tenant-scoped.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError
from core_app.db.models.crew import (
    Credential,
    CrewMember,
    Shift,
    ShiftStatus,
)
from core_app.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)

# Karolinska Sleepiness Scale thresholds
KSS_MAX_ALLOWED_FOR_SHIFT = 7  # Scores ≥ this value block shift assignment
KSS_WARNING_THRESHOLD = 5      # Scores ≥ this value trigger a warning event


class SchedulingService:
    """Manages shift assignments with credential validation and fatigue checks."""

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher

    # ── Crew member helpers ───────────────────────────────────────────────────

    async def get_crew_member(
        self, *, tenant_id: uuid.UUID, crew_member_id: uuid.UUID
    ) -> CrewMember:
        result = await self.db.execute(
            select(CrewMember).where(
                CrewMember.id == crew_member_id,
                CrewMember.tenant_id == tenant_id,
                CrewMember.deleted_at.is_(None),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError(
                code="CREW_MEMBER_NOT_FOUND",
                message="Crew member not found.",
                status_code=404,
                details={"crew_member_id": str(crew_member_id)},
            )
        return member

    # ── Credential enforcement ────────────────────────────────────────────────

    async def get_active_credentials(
        self, *, tenant_id: uuid.UUID, crew_member_id: uuid.UUID
    ) -> list[Credential]:
        """Return non-expired credentials for a crew member."""
        today = date.today()
        result = await self.db.execute(
            select(Credential).where(
                Credential.crew_member_id == crew_member_id,
                Credential.tenant_id == tenant_id,
                Credential.deleted_at.is_(None),
                Credential.expiry_date >= today,
            )
        )
        return list(result.scalars().all())

    async def assert_credentials_valid(
        self,
        *,
        tenant_id: uuid.UUID,
        crew_member_id: uuid.UUID,
        required_types: list[str] | None = None,
    ) -> list[Credential]:
        """Raise AppError if the crew member has expired or missing credentials.

        Args:
            tenant_id: Tenant UUID for zero-trust scoping.
            crew_member_id: Target crew member UUID.
            required_types: Optional list of credential type strings that must
                be present and active (e.g. ["NREMT-P", "BLS"]).

        Returns:
            List of active Credential objects.
        """
        active = await self.get_active_credentials(
            tenant_id=tenant_id, crew_member_id=crew_member_id
        )
        if required_types:
            active_types = {c.credential_type for c in active}
            missing = [t for t in required_types if t not in active_types]
            if missing:
                raise AppError(
                    code="CREDENTIAL_MISSING_OR_EXPIRED",
                    message="Crew member lacks required credentials.",
                    status_code=422,
                    details={
                        "crew_member_id": str(crew_member_id),
                        "missing_credential_types": missing,
                    },
                )
        return active

    # ── KSS fatigue logging ───────────────────────────────────────────────────

    async def log_kss_score(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        crew_member_id: uuid.UUID,
        kss_score: int,
        correlation_id: str | None = None,
    ) -> CrewMember:
        """Record a Karolinska Sleepiness Scale score for a crew member.

        KSS is a validated psychometric scale (1=extremely alert, 9=very sleepy).
        Scores ≥ KSS_MAX_ALLOWED_FOR_SHIFT are flagged; scheduling is blocked until
        the score is updated to an acceptable level.

        Args:
            tenant_id: Tenant UUID.
            actor_user_id: UUID of the user submitting the score.
            crew_member_id: Target crew member.
            kss_score: Integer 1–9.
            correlation_id: Optional trace ID.

        Returns:
            Updated CrewMember ORM instance.
        """
        if kss_score < 1 or kss_score > 9:
            raise AppError(
                code="KSS_SCORE_INVALID",
                message="KSS score must be between 1 and 9.",
                status_code=422,
                details={"kss_score": kss_score},
            )

        member = await self.get_crew_member(tenant_id=tenant_id, crew_member_id=crew_member_id)
        member.kss_score = kss_score
        member.kss_logged_at = datetime.now(UTC)
        self.db.add(member)
        await self.db.flush()

        event_name = "crew.kss_logged"
        payload: dict[str, Any] = {
            "crew_member_id": str(crew_member_id),
            "actor_user_id": str(actor_user_id),
            "kss_score": kss_score,
            "exceeds_threshold": kss_score >= KSS_MAX_ALLOWED_FOR_SHIFT,
            "warning": kss_score >= KSS_WARNING_THRESHOLD,
        }

        if kss_score >= KSS_MAX_ALLOWED_FOR_SHIFT:
            logger.warning(
                "scheduling_service.kss_score_high crew_member_id=%s kss=%d",
                crew_member_id,
                kss_score,
            )
            event_name = "crew.kss_high"

        await self.publisher.publish(
            event_name, tenant_id, crew_member_id, payload, correlation_id=correlation_id
        )
        await self.db.commit()
        return member

    # ── Shift assignment ──────────────────────────────────────────────────────

    async def assign_shift(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        crew_member_id: uuid.UUID,
        unit_identifier: str | None,
        shift_start: datetime,
        shift_end: datetime,
        required_credential_types: list[str] | None = None,
        notes: str | None = None,
        correlation_id: str | None = None,
    ) -> Shift:
        """Assign a crew member to a shift after credential and fatigue checks.

        Enforces:
        - Crew member must belong to the same tenant (zero-trust).
        - Crew member must have non-expired required credentials.
        - KSS score must be below KSS_MAX_ALLOWED_FOR_SHIFT.
        - shift_end must be after shift_start.

        Args:
            tenant_id: Tenant UUID for isolation.
            actor_user_id: Dispatching supervisor or admin UUID.
            crew_member_id: Target crew member.
            unit_identifier: Optional apparatus/unit label (e.g. "M-1").
            shift_start: Scheduled start time (timezone-aware).
            shift_end: Scheduled end time (timezone-aware).
            required_credential_types: Credential types that must be active.
            notes: Optional free-text notes.
            correlation_id: Optional trace ID.

        Returns:
            Persisted Shift ORM instance.
        """
        if shift_end <= shift_start:
            raise AppError(
                code="SHIFT_INVALID_TIME_RANGE",
                message="shift_end must be after shift_start.",
                status_code=422,
                details={
                    "shift_start": shift_start.isoformat(),
                    "shift_end": shift_end.isoformat(),
                },
            )

        member = await self.get_crew_member(tenant_id=tenant_id, crew_member_id=crew_member_id)

        if not member.is_active:
            raise AppError(
                code="CREW_MEMBER_INACTIVE",
                message="Cannot assign a shift to an inactive crew member.",
                status_code=422,
                details={"crew_member_id": str(crew_member_id)},
            )

        # KSS fatigue gate
        if (
            member.kss_score is not None
            and member.kss_score >= KSS_MAX_ALLOWED_FOR_SHIFT
        ):
            raise AppError(
                code="CREW_MEMBER_FATIGUE_BLOCKED",
                message=(
                    f"Crew member KSS fatigue score ({member.kss_score}) meets or exceeds "
                    f"the maximum allowed threshold ({KSS_MAX_ALLOWED_FOR_SHIFT}). "
                    "Update the KSS score before scheduling."
                ),
                status_code=422,
                details={
                    "crew_member_id": str(crew_member_id),
                    "kss_score": member.kss_score,
                    "kss_max_allowed": KSS_MAX_ALLOWED_FOR_SHIFT,
                },
            )

        # Credential gate
        await self.assert_credentials_valid(
            tenant_id=tenant_id,
            crew_member_id=crew_member_id,
            required_types=required_credential_types,
        )

        shift = Shift(
            tenant_id=tenant_id,
            crew_member_id=crew_member_id,
            unit_identifier=unit_identifier,
            shift_start=shift_start,
            shift_end=shift_end,
            status=ShiftStatus.SCHEDULED,
            kss_score_at_start=member.kss_score,
            notes=notes,
            version=1,
        )
        self.db.add(shift)
        await self.db.flush()

        await self.publisher.publish(
            "shift.assigned",
            tenant_id,
            shift.id,
            {
                "crew_member_id": str(crew_member_id),
                "actor_user_id": str(actor_user_id),
                "unit_identifier": unit_identifier,
                "shift_start": shift_start.isoformat(),
                "shift_end": shift_end.isoformat(),
                "kss_score_at_start": member.kss_score,
            },
            correlation_id=correlation_id,
        )
        await self.db.commit()
        logger.info(
            "scheduling_service.shift_assigned shift_id=%s crew_member_id=%s tenant_id=%s",
            shift.id,
            crew_member_id,
            tenant_id,
        )
        return shift

    async def get_shift(
        self, *, tenant_id: uuid.UUID, shift_id: uuid.UUID
    ) -> Shift:
        result = await self.db.execute(
            select(Shift).where(
                Shift.id == shift_id,
                Shift.tenant_id == tenant_id,
                Shift.deleted_at.is_(None),
            )
        )
        shift = result.scalar_one_or_none()
        if shift is None:
            raise AppError(
                code="SHIFT_NOT_FOUND",
                message="Shift not found.",
                status_code=404,
                details={"shift_id": str(shift_id)},
            )
        return shift

    async def list_shifts(
        self,
        *,
        tenant_id: uuid.UUID,
        crew_member_id: uuid.UUID | None = None,
        status: ShiftStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Shift]:
        """List shifts scoped to a tenant, with optional crew member and status filters."""
        stmt = select(Shift).where(
            Shift.tenant_id == tenant_id,
            Shift.deleted_at.is_(None),
        )
        if crew_member_id is not None:
            stmt = stmt.where(Shift.crew_member_id == crew_member_id)
        if status is not None:
            stmt = stmt.where(Shift.status == status)
        stmt = stmt.order_by(Shift.shift_start).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
