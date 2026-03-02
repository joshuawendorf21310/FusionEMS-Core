import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(
                code=ErrorCodes.TENANT_SCOPE_REQUIRED,
                message="Tenant scope is required for patient repository access.",
                status_code=400,
            )
        return tenant_id

    async def create(self, *, tenant_id: uuid.UUID, patient: Patient) -> Patient:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        patient.tenant_id = scoped_tenant_id
        self.db.add(patient)
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def get_by_id(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(Patient).where(
            Patient.id == patient_id,
            Patient.tenant_id == scoped_tenant_id,
            Patient.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def list_for_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> list[Patient]:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = (
            select(Patient)
            .where(
                Patient.tenant_id == scoped_tenant_id,
                Patient.incident_id == incident_id,
                Patient.deleted_at.is_(None),
            )
            .order_by(Patient.created_at.asc())
        )
        return list((await self.db.scalars(stmt)).all())

    async def count_for_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> int:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = (
            select(func.count())
            .select_from(Patient)
            .where(
                Patient.tenant_id == scoped_tenant_id,
                Patient.incident_id == incident_id,
                Patient.deleted_at.is_(None),
            )
        )
        return int((await self.db.scalar(stmt)) or 0)

    async def update_fields(self, *, tenant_id: uuid.UUID, patient: Patient) -> Patient:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        if patient.tenant_id != scoped_tenant_id:
            raise AppError(
                code=ErrorCodes.PATIENT_NOT_FOUND, message="Patient not found.", status_code=404
            )
        await self.db.flush()
        await self.db.refresh(patient)
        return patient
