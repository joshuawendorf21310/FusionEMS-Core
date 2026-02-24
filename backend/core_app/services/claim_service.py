import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.claim import Claim, ClaimStatus, allowed_claim_transition_targets
from core_app.repositories.claim_repository import ClaimRepository
from core_app.schemas.claim import (
    ClaimCreateRequest,
    ClaimListResponse,
    ClaimResponse,
    ClaimTransitionRequest,
    ClaimUpdateRequest,
)
from core_app.services.event_publisher import EventPublisher


class ClaimService:
    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.repository = ClaimRepository(db)

    async def create_claim(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, payload: ClaimCreateRequest, correlation_id: str | None) -> ClaimResponse:
        claim = Claim(tenant_id=tenant_id, status=ClaimStatus.DRAFT, version=1, **payload.model_dump())
        created = await self.repository.create(tenant_id=tenant_id, claim=claim)
        await self._write_audit_log(tenant_id, actor_user_id, created.id, "claim.created", list(payload.model_dump().keys()) + ["status"], correlation_id)
        await self.db.commit()
        return ClaimResponse.model_validate(created)

    async def list_claims(self, *, tenant_id: uuid.UUID, status: ClaimStatus | None, payer_type, submitted_from, submitted_to) -> ClaimListResponse:
        items = await self.repository.list_filtered(
            tenant_id=tenant_id, status=status, payer_type=payer_type, submitted_from=submitted_from, submitted_to=submitted_to
        )
        total = await self.repository.count_filtered(tenant_id=tenant_id, status=status, payer_type=payer_type)
        return ClaimListResponse(items=[ClaimResponse.model_validate(item) for item in items], total=total)

    async def get_claim(self, *, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> ClaimResponse:
        return ClaimResponse.model_validate(await self._require_claim(tenant_id=tenant_id, claim_id=claim_id))

    async def update_claim(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, claim_id: uuid.UUID, payload: ClaimUpdateRequest, correlation_id: str | None) -> ClaimResponse:
        claim = await self._require_claim(tenant_id=tenant_id, claim_id=claim_id)
        self._enforce_version(claim=claim, version=payload.version)
        changed: list[str] = []
        for field_name, value in payload.model_dump(exclude={"version"}, exclude_none=True).items():
            if getattr(claim, field_name) != value:
                setattr(claim, field_name, value)
                changed.append(field_name)
        claim.version += 1
        changed.append("version")
        updated = await self.repository.update(tenant_id=tenant_id, claim=claim)
        await self._write_audit_log(tenant_id, actor_user_id, updated.id, "claim.updated", changed, correlation_id)
        await self.db.commit()
        await self.publisher.publish("claim.updated", tenant_id, updated.id, {"changed_fields": changed})
        return ClaimResponse.model_validate(updated)

    async def transition_claim(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, claim_id: uuid.UUID, payload: ClaimTransitionRequest, correlation_id: str | None) -> ClaimResponse:
        claim = await self._require_claim(tenant_id=tenant_id, claim_id=claim_id)
        self._enforce_version(claim=claim, version=payload.version)
        allowed = allowed_claim_transition_targets(claim.status)
        if payload.target_status not in allowed:
            raise AppError(
                code=ErrorCodes.CLAIM_INVALID_TRANSITION,
                message="Invalid claim status transition.",
                status_code=422,
                details={"from_status": claim.status.value, "to_status": payload.target_status.value, "allowed_targets": [s.value for s in sorted(allowed, key=lambda s: s.value)]},
            )
        from_status = claim.status
        claim.status = payload.target_status
        claim.version += 1
        updated = await self.repository.update(tenant_id=tenant_id, claim=claim)
        await self._write_audit_log(tenant_id, actor_user_id, updated.id, "claim.status_changed", ["status", "version"], correlation_id)
        await self.db.commit()
        await self.publisher.publish("claim.status_changed", tenant_id, updated.id, {"from_status": from_status.value, "to_status": updated.status.value})
        return ClaimResponse.model_validate(updated)

    async def _require_claim(self, *, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> Claim:
        claim = await self.repository.get_by_id(tenant_id=tenant_id, claim_id=claim_id)
        if claim is None:
            raise AppError(code=ErrorCodes.CLAIM_NOT_FOUND, message="Claim not found.", status_code=404, details={"claim_id": str(claim_id)})
        return claim

    @staticmethod
    def _enforce_version(*, claim: Claim, version: int) -> None:
        if claim.version != version:
            raise AppError(
                code=ErrorCodes.CONCURRENCY_CONFLICT,
                message="Claim version conflict.",
                status_code=409,
                details={"expected_version": version, "server_version": claim.version, "updated_at": claim.updated_at.isoformat()},
            )

    async def _write_audit_log(self, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, entity_id: uuid.UUID, action: str, changed_fields: list[str], correlation_id: str | None) -> None:
        self.db.add(
            AuditLog(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_name="claim",
                entity_id=entity_id,
                field_changes={"changed_fields": changed_fields, "metadata": {}},
                correlation_id=correlation_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.db.flush()
