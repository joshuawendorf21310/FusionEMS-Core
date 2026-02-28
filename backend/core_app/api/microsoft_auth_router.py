"""Microsoft Entra ID (Azure AD) authorization code flow.

Endpoints:
  GET  /auth/microsoft/login    — Redirect to Entra authorize URL
  GET  /auth/microsoft/callback — Exchange code for tokens, issue JWT, redirect to frontend
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.core.security import create_access_token
from core_app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

_AUTHORIZE_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
_SCOPES = "openid email profile"

_active_states: dict[str, bool] = {}


def _check_entra_configured() -> None:
    s = get_settings()
    if not all([s.graph_tenant_id, s.graph_client_id, s.graph_client_secret]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft Entra login is not configured",
        )


@router.get("/login")
def microsoft_login() -> RedirectResponse:
    _check_entra_configured()
    s = get_settings()
    state = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    _active_states[state] = True
    params = {
        "client_id": s.graph_client_id,
        "response_type": "code",
        "redirect_uri": s.microsoft_redirect_uri,
        "scope": _SCOPES,
        "response_mode": "query",
        "state": state,
    }
    url = _AUTHORIZE_URL.format(tenant_id=s.graph_tenant_id) + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=url, status_code=302)


def _exchange_code(code: str) -> dict[str, Any]:
    import json as _json

    s = get_settings()
    body = urllib.parse.urlencode({
        "client_id": s.graph_client_id,
        "client_secret": s.graph_client_secret,
        "code": code,
        "redirect_uri": s.microsoft_redirect_uri,
        "grant_type": "authorization_code",
        "scope": _SCOPES,
    }).encode("utf-8")
    req = urllib.request.Request(
        _TOKEN_URL.format(tenant_id=s.graph_tenant_id),
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("entra_token_exchange_failed status=%d body=%.300s", exc.code, error_body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Entra",
        ) from exc


def _fetch_userinfo(access_token: str) -> dict[str, Any]:
    import json as _json

    req = urllib.request.Request(_USERINFO_URL, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("entra_userinfo_failed status=%d body=%.300s", exc.code, error_body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from Microsoft Graph",
        ) from exc


@router.get("/callback")
def microsoft_callback(
    request: Request,
    code: str = Query(default=""),
    error: str = Query(default=""),
    error_description: str = Query(default=""),
    state: str = Query(default=""),
    db: Session = Depends(db_session_dependency),
) -> RedirectResponse:
    _check_entra_configured()
    s = get_settings()

    if error:
        logger.warning("entra_callback_error error=%s desc=%s", error, error_description)
        return RedirectResponse(
            url=f"{s.microsoft_post_login_url}?error=entra_denied",
            status_code=302,
        )

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")

    if state not in _active_states:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state parameter")
    _active_states.pop(state, None)

    token_data = _exchange_code(code)
    ms_access_token: str = token_data.get("access_token", "")
    if not ms_access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No access_token in Entra response")

    userinfo = _fetch_userinfo(ms_access_token)
    email: str = (userinfo.get("mail") or userinfo.get("userPrincipalName") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No email in Microsoft profile")

    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)
    if user is None:
        logger.warning("entra_login_no_matching_user email=%s", email)
        return RedirectResponse(
            url=f"{s.microsoft_post_login_url}?error=no_account",
            status_code=302,
        )

    jwt_token = create_access_token(str(user.id), str(user.tenant_id), user.role)
    logger.info("entra_login_success user_id=%s email=%s", user.id, email)

    redirect_url = f"{s.microsoft_post_login_url}?token={jwt_token}"
    return RedirectResponse(url=redirect_url, status_code=302)
