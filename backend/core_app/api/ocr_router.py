import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.ocr import (
    OcrApplyRequest,
    OcrApproveRequest,
    OcrPresignRequest,
    OcrPresignResponse,
    OcrProposedChangesResponse,
    OcrUploadRegisterRequest,
    OcrUploadResponse,
)
from core_app.services.ocr_service import OcrService

router = APIRouter(prefix="/ocr/uploads", tags=["ocr"])


def ocr_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> OcrService:
    return OcrService(db)


@router.post("/presign", response_model=OcrPresignResponse)
async def presign_upload(
    payload: OcrPresignRequest,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: OcrService = Depends(ocr_service_dependency),
) -> OcrPresignResponse:
    return await service.presign_upload(tenant_id=current_user.tenant_id, filename=payload.filename)


@router.post("", response_model=OcrUploadResponse, status_code=status.HTTP_201_CREATED)
async def register_upload(
    payload: OcrUploadRegisterRequest,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: OcrService = Depends(ocr_service_dependency),
) -> OcrUploadResponse:
    return await service.register_upload(tenant_id=current_user.tenant_id, payload=payload)


@router.patch("/{upload_id}/approve", response_model=OcrProposedChangesResponse)
async def approve_upload(
    upload_id: uuid.UUID,
    payload: OcrApproveRequest,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: OcrService = Depends(ocr_service_dependency),
) -> OcrProposedChangesResponse:
    return await service.approve_upload(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        upload_id=upload_id,
        payload=payload,
    )


@router.post("/{upload_id}/apply", response_model=OcrUploadResponse)
async def apply_upload(
    upload_id: uuid.UUID,
    payload: OcrApplyRequest,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: OcrService = Depends(ocr_service_dependency),
) -> OcrUploadResponse:
    return await service.apply_upload(
        tenant_id=current_user.tenant_id,
        upload_id=upload_id,
        payload=payload,
    )
