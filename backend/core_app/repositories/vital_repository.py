import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.vital import Vital


class VitalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(
                code=ErrorCodes.TENANT_SCOPE_REQUIRED,
                message="Tenant scope is required for vital repository access.",
                status_code=400,
            )
        return tenant_id

    async def create(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        vital.tenant_id = scoped_tenant_id
        self.db.add(vital)
        await self.db.flush()
        await self.db.refresh(vital)
        return vital

    async def get_by_id(self, *, tenant_id: uuid.UUID, vital_id: uuid.UUID) -> Vital | None:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = select(Vital).where(
            Vital.id == vital_id,
            Vital.tenant_id == scoped_tenant_id,
            Vital.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def list_for_patient(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> list[Vital]:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = (
            select(Vital)
            .where(
                Vital.tenant_id == scoped_tenant_id,
                Vital.patient_id == patient_id,
                Vital.deleted_at.is_(None),
            )
            .order_by(Vital.taken_at.desc())
        )
        return list((await self.db.scalars(stmt)).all())

    async def count_for_patient(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> int:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        stmt = (
            select(func.count())
            .select_from(Vital)
            .where(
                Vital.tenant_id == scoped_tenant_id,
                Vital.patient_id == patient_id,
                Vital.deleted_at.is_(None),
            )
        )
        return int((await self.db.scalar(stmt)) or 0)

    async def update_fields(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        if vital.tenant_id != scoped_tenant_id:
            raise AppError(
                code=ErrorCodes.VITAL_NOT_FOUND, message="Vital not found.", status_code=404
            )
        await self.db.flush()
        await self.db.refresh(vital)
        return vital

    async def soft_delete(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        scoped_tenant_id = self._require_tenant_scope(tenant_id)
        if vital.tenant_id != scoped_tenant_id:
            raise AppError(
                code=ErrorCodes.VITAL_NOT_FOUND, message="Vital not found.", status_code=404
            )
        vital.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(vital)
        return vital
