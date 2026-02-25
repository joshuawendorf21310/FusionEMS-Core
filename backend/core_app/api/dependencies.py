from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

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

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role")
        if not subject or not tenant_id or not role:
            raise unauthorized
    except JWTError as exc:
        raise unauthorized from exc

    user_repo = UserRepository(db)
    user = user_repo.get_by_id_and_tenant(UUID(subject), UUID(tenant_id))
    if user is None:
        raise unauthorized

    current = CurrentUser(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    request.state.tenant_id = current.tenant_id
    request.state.user_id = current.user_id
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


def get_tenant_id(request: Request, current_user: CurrentUser = Depends(get_current_user)) -> UUID:
    request.state.tenant_id = current_user.tenant_id
    request.state.user_id = current_user.user_id
    return current_user.tenant_id


def get_current_user_optional(request: Request, db: Session = Depends(get_db_session)):
    """Optional auth for bootstrap screens. Returns None if no/invalid token."""
    try:
        return get_current_user(request=request, db=db)
    except Exception:
        return None
