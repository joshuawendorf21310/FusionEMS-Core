import uuid

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.ocr import OCRUpload, OcrSourceType
from core_app.schemas.ocr import OcrApplyRequest, OcrApproveRequest
from core_app.services.ocr_service import OcrService


class FakeDB:
    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None


class FakeRepo:
    def __init__(self, upload: OCRUpload | None):
        self.upload = upload

    async def get(self, *, tenant_id, upload_id):
        if self.upload and self.upload.id == upload_id and self.upload.tenant_id == tenant_id:
            return self.upload
        return None


@pytest.mark.asyncio
async def test_ocr_apply_requires_approval() -> None:
    tenant_id = uuid.uuid4()
    upload = OCRUpload(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_id=uuid.uuid4(),
        source_type=OcrSourceType.DOCUMENT,
        s3_object_key="k",
        image_sha256="x",
        extracted_json_encrypted=b"e30=",
        confidence_score=0.8,
        model_version="v1",
        approved_flag=False,
        approved_by_user_id=None,
        approved_at=None,
        applied_to_entity_type=None,
        applied_to_entity_id=None,
        version=1,
    )
    service = OcrService(FakeDB())
    service.repo = FakeRepo(upload)
    with pytest.raises(AppError) as exc:
        await service.apply_upload(
            tenant_id=tenant_id,
            upload_id=upload.id,
            payload=OcrApplyRequest(version=1, selected_fields={}, applied_to_entity_type="vital", applied_to_entity_id=uuid.uuid4()),
        )
    assert exc.value.code == ErrorCodes.OCR_APPROVAL_REQUIRED


@pytest.mark.asyncio
async def test_ocr_approve_conflict() -> None:
    tenant_id = uuid.uuid4()
    upload = OCRUpload(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_id=uuid.uuid4(),
        source_type=OcrSourceType.DOCUMENT,
        s3_object_key="k",
        image_sha256="x",
        extracted_json_encrypted=b"e30=",
        confidence_score=0.8,
        model_version="v1",
        approved_flag=False,
        approved_by_user_id=None,
        approved_at=None,
        applied_to_entity_type=None,
        applied_to_entity_id=None,
        version=3,
    )
    service = OcrService(FakeDB())
    service.repo = FakeRepo(upload)
    with pytest.raises(AppError) as exc:
        await service.approve_upload(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            upload_id=upload.id,
            payload=OcrApproveRequest(version=1),
        )
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT
