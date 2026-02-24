import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.integration_registry import IntegrationProvider, IntegrationRegistry


class IntegrationRegistryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(
                code=ErrorCodes.TENANT_SCOPE_REQUIRED,
                message="Tenant scope is required for integration registry access.",
                status_code=400,
            )
        return tenant_id

    async def list_for_tenant(self, *, tenant_id: uuid.UUID) -> list[IntegrationRegistry]:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(IntegrationRegistry).where(
            IntegrationRegistry.tenant_id == scoped_tenant_id,
            IntegrationRegistry.deleted_at.is_(None),
        )
        return list((await self.db.scalars(stmt)).all())

    async def get_by_provider(
        self, *, tenant_id: uuid.UUID, provider: IntegrationProvider
    ) -> IntegrationRegistry | None:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(IntegrationRegistry).where(
            IntegrationRegistry.tenant_id == scoped_tenant_id,
            IntegrationRegistry.provider_name == provider,
            IntegrationRegistry.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def create(self, *, tenant_id: uuid.UUID, entry: IntegrationRegistry) -> IntegrationRegistry:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        entry.tenant_id = scoped_tenant_id
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def update(self, *, tenant_id: uuid.UUID, entry: IntegrationRegistry) -> IntegrationRegistry:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        if entry.tenant_id != scoped_tenant_id:
            raise AppError(
                code=ErrorCodes.INTEGRATION_NOT_FOUND,
                message="Integration provider not found.",
                status_code=404,
            )
        await self.db.flush()
        await self.db.refresh(entry)
        return entry
