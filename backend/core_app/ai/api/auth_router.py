from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import LoginRequest, TokenResponse
from core_app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session_dependency)) -> TokenResponse:
    service = AuthService(UserRepository(db))
    try:
        return service.login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh() -> TokenResponse:
    # Codex must implement: refresh token rotation (Redis-backed) and return a new access token
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")

@router.post("/logout")
def logout() -> dict:
    # Codex must implement: revoke refresh token / session
    return {"status": "ok"}
