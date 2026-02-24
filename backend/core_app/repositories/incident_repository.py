import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.incident import Incident


class IncidentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(
                code=ErrorCodes.TENANT_SCOPE_REQUIRED,
                message="Tenant scope is required for incident repository access.",
                status_code=400,
            )
        return tenant_id

    async def create(self, *, tenant_id: uuid.UUID, incident: Incident) -> Incident:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        incident.tenant_id = scoped_tenant_id
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def get_by_id(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident | None:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(Incident).where(
            Incident.id == incident_id,
            Incident.tenant_id == scoped_tenant_id,
            Incident.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def list_paginated(self, *, tenant_id: uuid.UUID, limit: int, offset: int) -> list[Incident]:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = (
            select(Incident)
            .where(Incident.tenant_id == scoped_tenant_id, Incident.deleted_at.is_(None))
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.db.scalars(stmt)).all())

    async def count(self, *, tenant_id: uuid.UUID) -> int:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(func.count()).select_from(Incident).where(
            Incident.tenant_id == scoped_tenant_id,
            Incident.deleted_at.is_(None),
        )
        return int((await self.db.scalar(stmt)) or 0)

    async def update_fields(self, *, tenant_id: uuid.UUID, incident: Incident) -> Incident:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        if incident.tenant_id != scoped_tenant_id:
            raise AppError(
                code=ErrorCodes.INCIDENT_NOT_FOUND,
                message="Incident not found.",
                status_code=404,
            )
        await self.db.flush()
        await self.db.refresh(incident)
        return incident
