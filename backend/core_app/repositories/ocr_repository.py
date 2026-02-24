import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.ocr import OCRUpload


class OcrRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _tenant(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope required.", status_code=400)
        return tenant_id

    async def create(self, *, tenant_id: uuid.UUID, upload: OCRUpload) -> OCRUpload:
        upload.tenant_id = self._tenant(tenant_id)
        self.db.add(upload)
        await self.db.flush(); await self.db.refresh(upload)
        return upload

    async def get(self, *, tenant_id: uuid.UUID, upload_id: uuid.UUID) -> OCRUpload | None:
        stmt = select(OCRUpload).where(OCRUpload.id == upload_id, OCRUpload.tenant_id == self._tenant(tenant_id), OCRUpload.deleted_at.is_(None))
        return await self.db.scalar(stmt)
