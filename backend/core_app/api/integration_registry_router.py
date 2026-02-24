from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.core.config import get_settings
from core_app.core.encryption.envelope import KmsEnvelopeEncryptor
from core_app.db.session import get_async_db_session
from core_app.models.integration_registry import IntegrationProvider
from core_app.schemas.auth import CurrentUser
from core_app.schemas.integration_registry import (
    IntegrationEnableDisableRequest,
    IntegrationEventResponse,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationUpsertRequest,
)
from core_app.services.event_publisher import NoOpEventPublisher
from core_app.services.integration_registry_service import IntegrationRegistryService

router = APIRouter(prefix="/integrations", tags=["integrations"])


def service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> IntegrationRegistryService:
    settings = get_settings()
    encryptor = KmsEnvelopeEncryptor(
        kms_key_id=settings.aws_kms_integration_key_id,
        region_name=settings.aws_region,
    )
    return IntegrationRegistryService(db=db, publisher=NoOpEventPublisher(), encryptor=encryptor)


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    service: IntegrationRegistryService = Depends(service_dependency),
    current_user: CurrentUser = Depends(require_role("admin", "founder", "ems", "billing")),
) -> IntegrationListResponse:
    return await service.list_integrations(tenant_id=current_user.tenant_id)


@router.get("/{provider}", response_model=IntegrationResponse)
async def get_integration(
    provider: IntegrationProvider,
    service: IntegrationRegistryService = Depends(service_dependency),
    current_user: CurrentUser = Depends(require_role("admin", "founder", "ems", "billing")),
) -> IntegrationResponse:
    return await service.get_integration(tenant_id=current_user.tenant_id, provider=provider)


@router.post("/{provider}", response_model=IntegrationResponse)
async def upsert_integration(
    provider: IntegrationProvider,
    payload: IntegrationUpsertRequest,
    request: Request,
    service: IntegrationRegistryService = Depends(service_dependency),
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
) -> IntegrationResponse:
    return await service.upsert_integration(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        provider=provider,
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.patch("/{provider}/enable", response_model=IntegrationEventResponse)
async def enable_integration(
    provider: IntegrationProvider,
    payload: IntegrationEnableDisableRequest,
    request: Request,
    service: IntegrationRegistryService = Depends(service_dependency),
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
) -> IntegrationEventResponse:
    return await service.set_enabled(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        provider=provider,
        version=payload.version,
        enabled_flag=True,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.patch("/{provider}/disable", response_model=IntegrationEventResponse)
async def disable_integration(
    provider: IntegrationProvider,
    payload: IntegrationEnableDisableRequest,
    request: Request,
    service: IntegrationRegistryService = Depends(service_dependency),
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
) -> IntegrationEventResponse:
    return await service.set_enabled(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        provider=provider,
        version=payload.version,
        enabled_flag=False,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
