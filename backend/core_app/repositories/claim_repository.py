import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.claim import Claim, ClaimStatus, PayerType


class ClaimRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope is required.", status_code=400)
        return tenant_id

    async def create(self, *, tenant_id: uuid.UUID, claim: Claim) -> Claim:
        claim.tenant_id = self._require_tenant_scope(tenant_id)
        self.db.add(claim)
        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def get_by_id(self, *, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> Claim | None:
        scoped = self._require_tenant_scope(tenant_id)
        stmt = select(Claim).where(Claim.id == claim_id, Claim.tenant_id == scoped, Claim.deleted_at.is_(None))
        return await self.db.scalar(stmt)


    async def get_by_idempotency_key(self, *, tenant_id: uuid.UUID, idempotency_key: str) -> Claim | None:
        scoped = self._require_tenant_scope(tenant_id)
        stmt = select(Claim).where(
            Claim.tenant_id == scoped,
            Claim.idempotency_key == idempotency_key,
            Claim.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def list_filtered(
        self,
        *,
        tenant_id: uuid.UUID,
        status: ClaimStatus | None,
        payer_type: PayerType | None,
        submitted_from: datetime | None,
        submitted_to: datetime | None,
    ) -> list[Claim]:
        scoped = self._require_tenant_scope(tenant_id)
        stmt = select(Claim).where(Claim.tenant_id == scoped, Claim.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Claim.status == status)
        if payer_type is not None:
            stmt = stmt.where(Claim.payer_type == payer_type)
        if submitted_from is not None:
            stmt = stmt.where(Claim.submitted_at >= submitted_from)
        if submitted_to is not None:
            stmt = stmt.where(Claim.submitted_at <= submitted_to)
        stmt = stmt.order_by(Claim.created_at.desc())
        return list((await self.db.scalars(stmt)).all())

    async def count_filtered(self, *, tenant_id: uuid.UUID, status: ClaimStatus | None, payer_type: PayerType | None) -> int:
        scoped = self._require_tenant_scope(tenant_id)
        stmt = select(func.count()).select_from(Claim).where(Claim.tenant_id == scoped, Claim.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Claim.status == status)
        if payer_type is not None:
            stmt = stmt.where(Claim.payer_type == payer_type)
        return int((await self.db.scalar(stmt)) or 0)

    async def update(self, *, tenant_id: uuid.UUID, claim: Claim) -> Claim:
        if claim.tenant_id != self._require_tenant_scope(tenant_id):
            raise AppError(code=ErrorCodes.CLAIM_NOT_FOUND, message="Claim not found.", status_code=404)
        await self.db.flush()
        await self.db.refresh(claim)
        return claim
