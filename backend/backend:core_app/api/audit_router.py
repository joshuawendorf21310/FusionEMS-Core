from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.repositories.audit_repository import AuditRepository
from core_app.schemas.audit import AuditLogResponse, AuditMutationRequest
from core_app.schemas.auth import CurrentUser
from core_app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
def list_logs(
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AuditLogResponse]:
    rows = AuditRepository(db).list_for_tenant(current_user.tenant_id)
    return [AuditLogResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/logs", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_log(
    payload: AuditMutationRequest,
    request: Request,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditLogResponse:
    service = AuditService(db)
    row = service.log_mutation(
        tenant_id=current_user.tenant_id,
        action=payload.action,
        entity_name=payload.entity_name,
        entity_id=payload.entity_id,
        actor_user_id=current_user.user_id,
        field_changes=payload.field_changes,
        correlation_id=request.state.correlation_id,
    )
    db.commit()
    return AuditLogResponse.model_validate(row, from_attributes=True)
