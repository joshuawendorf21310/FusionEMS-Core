from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from core_app.services.cognito_jwt import verify_cognito_jwt, CognitoAuthError
from core_app.services.opa import check_policy, opa_enabled, OpaError
from sqlalchemy.orm import Session
from sqlalchemy import text

from core_app.core.config import get_settings
from core_app.db.session import get_db_session
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import CurrentUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def db_session_dependency(db: Session = Depends(get_db_session)) -> Session:
    return db


def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(db_session_dependency)
) -> CurrentUser:
    settings = get_settings()
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_repo = UserRepository(db)

    if settings.auth_mode.lower() == "cognito":
        try:
            claims = verify_cognito_jwt(token)
        except CognitoAuthError as exc:
            raise unauthorized from exc

        if not claims.tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant claim")

        # Map role from claim, then groups, then default
        role = claims.role
        if not role and claims.groups:
            # Lowest common denominator mapping
            if "Founder" in claims.groups or "PlatformSuperAdmin" in claims.groups:
                role = "founder"
            elif "AgencyAdmin" in claims.groups:
                role = "agency_admin"
            elif "BillingSpecialist" in claims.groups:
                role = "billing"
            elif "ClinicalProvider" in claims.groups:
                role = "ems"
            else:
                role = "viewer"
        role = role or "viewer"

        tenant_uuid = UUID(str(claims.tenant_id))
        email = (claims.email or "").lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing email claim")

        user = user_repo.get_by_email_and_tenant(email, tenant_uuid)
        if user is None:
            # Auto-provision first-login user row (no local password; cognito is source of truth)
            user = user_repo.create(tenant_id=tenant_uuid, email=email, hashed_password="COGNITO", role=role)

        current = CurrentUser(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    else:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            subject = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            role = payload.get("role")
            if not subject or not tenant_id or not role:
                raise unauthorized
        except JWTError as exc:
            raise unauthorized from exc

        user = user_repo.get_by_id_and_tenant(UUID(subject), UUID(tenant_id))
        if user is None:
            raise unauthorized

        current = CurrentUser(user_id=user.id, tenant_id=user.tenant_id, role=user.role)

    request.state.tenant_id = current.tenant_id
    request.state.user_id = current.user_id
    # Enforce database tenant isolation via Postgres RLS
    db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(current.tenant_id)})

    if hasattr(request.state, "audit_context"):
        request.state.audit_context["tenant_id"] = str(current.tenant_id)
        request.state.audit_context["actor_user_id"] = str(current.user_id)
    return current


def require_role(*allowed_roles: str):
    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return _dependency


def require_permission(permission: str):
    def _dependency(request: Request, current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if opa_enabled():
            input_doc = {
                "tenant_id": str(current_user.tenant_id),
                "user_id": str(current_user.user_id),
                "role": current_user.role,
                "permission": permission,
                "path": str(request.url.path),
                "method": request.method,
            }
            try:
                allowed = check_policy(input_doc)
            except OpaError as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OPA unavailable") from exc
            if not allowed:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return _dependency


def get_tenant_id(request: Request, current_user: CurrentUser = Depends(get_current_user)) -> UUID:
    request.state.tenant_id = current_user.tenant_id
    request.state.user_id = current_user.user_id
    return current_user.tenant_id
