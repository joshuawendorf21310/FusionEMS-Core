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

    async def list_paginated(self, *, tenant_id: uuid.UUID, limit: int, offset: int) -> tuple[list[Incident], int]:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        list_stmt = (
            select(Incident)
            .where(Incident.tenant_id == scoped_tenant_id, Incident.deleted_at.is_(None))
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Incident).where(
            Incident.tenant_id == scoped_tenant_id,
            Incident.deleted_at.is_(None),
        )
        incidents = list((await self.db.scalars(list_stmt)).all())
        total = int((await self.db.scalar(count_stmt)) or 0)
        return incidents, total

    async def save(self, *, tenant_id: uuid.UUID, incident: Incident) -> Incident:
        self._require_tenant_scope(tenant_id)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident
