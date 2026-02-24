import base64
import json
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.ocr import OCRUpload
from core_app.repositories.ocr_repository import OcrRepository
from core_app.schemas.ocr import (
    OcrApplyRequest,
    OcrApproveRequest,
    OcrPresignResponse,
    OcrProposedChangesResponse,
    OcrUploadRegisterRequest,
    OcrUploadResponse,
)


class OcrService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OcrRepository(db)

    @staticmethod
    def _encrypt_json(data: dict) -> bytes:
        return base64.b64encode(json.dumps(data, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def _decrypt_json(data: bytes) -> dict:
        return json.loads(base64.b64decode(data).decode("utf-8"))

    async def presign_upload(self, *, tenant_id: uuid.UUID, filename: str) -> OcrPresignResponse:
        key = f"ocr/{tenant_id}/{uuid.uuid4()}-{filename}"
        return OcrPresignResponse(upload_url=f"https://example-upload.local/{key}?signature=mock", object_key=key)

    async def register_upload(self, *, tenant_id: uuid.UUID, payload: OcrUploadRegisterRequest) -> OcrUploadResponse:
        upload = OCRUpload(
            tenant_id=tenant_id,
            version=1,
            approved_flag=False,
            approved_by_user_id=None,
            approved_at=None,
            applied_to_entity_type=None,
            applied_to_entity_id=None,
            incident_id=payload.incident_id,
            source_type=payload.source_type,
            s3_object_key=payload.s3_object_key,
            image_sha256=payload.image_sha256,
            extracted_json_encrypted=self._encrypt_json(payload.extracted_json),
            confidence_score=payload.confidence_score,
            model_version=payload.model_version,
        )
        created = await self.repo.create(tenant_id=tenant_id, upload=upload)
        await self.db.commit()
        return OcrUploadResponse.model_validate(created)

    async def approve_upload(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, upload_id: uuid.UUID, payload: OcrApproveRequest) -> OcrProposedChangesResponse:
        upload = await self._require_upload(tenant_id=tenant_id, upload_id=upload_id)
        if upload.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="OCR upload version conflict.", status_code=409, details={"server_version": upload.version, "updated_at": (upload.updated_at.isoformat() if upload.updated_at else None)})
        upload.approved_flag = True
        upload.approved_by_user_id = actor_user_id
        upload.approved_at = datetime.now(UTC)
        upload.version += 1
        await self.db.flush(); await self.db.refresh(upload)
        await self.db.commit()
        proposed = self._decrypt_json(upload.extracted_json_encrypted)
        return OcrProposedChangesResponse(upload_id=upload.id, approved_flag=True, selected_fields=proposed)

    async def apply_upload(self, *, tenant_id: uuid.UUID, upload_id: uuid.UUID, payload: OcrApplyRequest) -> OcrUploadResponse:
        upload = await self._require_upload(tenant_id=tenant_id, upload_id=upload_id)
        if not upload.approved_flag:
            raise AppError(code=ErrorCodes.OCR_APPROVAL_REQUIRED, message="OCR upload must be approved before apply.", status_code=422)
        if upload.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="OCR upload version conflict.", status_code=409, details={"server_version": upload.version, "updated_at": (upload.updated_at.isoformat() if upload.updated_at else None)})

        upload.applied_to_entity_type = payload.applied_to_entity_type
        upload.applied_to_entity_id = payload.applied_to_entity_id
        upload.version += 1
        await self.db.flush(); await self.db.refresh(upload)
        await self.db.commit()
        return OcrUploadResponse.model_validate(upload)

    async def _require_upload(self, *, tenant_id: uuid.UUID, upload_id: uuid.UUID) -> OCRUpload:
        upload = await self.repo.get(tenant_id=tenant_id, upload_id=upload_id)
        if upload is None:
            raise AppError(code=ErrorCodes.OCR_UPLOAD_NOT_FOUND, message="OCR upload not found.", status_code=404)
        return upload
