import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.idempotency_receipt import IdempotencyReceipt


class IdempotencyReceiptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(
                code=ErrorCodes.TENANT_SCOPE_REQUIRED,
                message="Tenant scope is required for idempotency receipt access.",
                status_code=400,
            )
        return tenant_id

    async def get_by_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str, route_key: str
    ) -> IdempotencyReceipt | None:
        scoped = self._require_tenant_scope(tenant_id)
        stmt = select(IdempotencyReceipt).where(
            IdempotencyReceipt.tenant_id == scoped,
            IdempotencyReceipt.idempotency_key == idempotency_key,
            IdempotencyReceipt.route_key == route_key,
        )
        return await self.db.scalar(stmt)

    async def create(self, *, tenant_id: uuid.UUID, receipt: IdempotencyReceipt) -> IdempotencyReceipt:
        scoped = self._require_tenant_scope(tenant_id)
        receipt.tenant_id = scoped
        self.db.add(receipt)
        await self.db.flush()
        await self.db.refresh(receipt)
        return receipt
