import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.fire import FireIncident, FireInspection, FireInspectionViolation, InspectionProperty


class FireRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _tenant(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope required.", status_code=400)
        return tenant_id

    async def create_incident(self, *, tenant_id: uuid.UUID, incident: FireIncident) -> FireIncident:
        incident.tenant_id = self._tenant(tenant_id)
        self.db.add(incident)
        await self.db.flush(); await self.db.refresh(incident)
        return incident

    async def get_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> FireIncident | None:
        stmt = select(FireIncident).where(FireIncident.id == incident_id, FireIncident.tenant_id == self._tenant(tenant_id), FireIncident.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def create_property(self, *, tenant_id: uuid.UUID, prop: InspectionProperty) -> InspectionProperty:
        prop.tenant_id = self._tenant(tenant_id)
        self.db.add(prop)
        await self.db.flush(); await self.db.refresh(prop)
        return prop

    async def get_property(self, *, tenant_id: uuid.UUID, property_id: uuid.UUID) -> InspectionProperty | None:
        stmt = select(InspectionProperty).where(InspectionProperty.id == property_id, InspectionProperty.tenant_id == self._tenant(tenant_id), InspectionProperty.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def create_inspection(self, *, tenant_id: uuid.UUID, inspection: FireInspection) -> FireInspection:
        inspection.tenant_id = self._tenant(tenant_id)
        self.db.add(inspection)
        await self.db.flush(); await self.db.refresh(inspection)
        return inspection

    async def create_violation(self, *, tenant_id: uuid.UUID, violation: FireInspectionViolation) -> FireInspectionViolation:
        violation.tenant_id = self._tenant(tenant_id)
        self.db.add(violation)
        await self.db.flush(); await self.db.refresh(violation)
        return violation
