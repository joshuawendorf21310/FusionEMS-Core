"""Microsoft Entra ID (Azure AD) authorization code flow.

Endpoints:
  GET  /auth/microsoft/login    — Redirect to Entra authorize URL
  GET  /auth/microsoft/callback — Exchange code for tokens, issue JWT, redirect to frontend
  GET  /auth/microsoft/logout   — Redirect to Entra logout, then back to frontend login page
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
_LOGOUT_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
_SCOPES = "openid email profile User.Read"

_STATE_TTL_SECONDS = 600


def _sign_state(nonce: str) -> str:
    s = get_settings()
    payload = f"{nonce}|{int(__import__('time').time())}"
    sig = hmac.new(s.jwt_secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def _verify_state(state: str) -> bool:
    s = get_settings()
    parts = state.split("|")
    if len(parts) != 3:
        return False
    nonce, ts_str, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if abs(time.time() - ts) > _STATE_TTL_SECONDS:
        return False
    expected_payload = f"{nonce}|{ts_str}"
    expected_sig = hmac.new(
        s.jwt_secret_key.encode(), expected_payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected_sig)


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
    state = _sign_state(secrets.token_hex(16))
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
    s = get_settings()
    body = urllib.parse.urlencode(
        {
            "client_id": s.graph_client_id,
            "client_secret": s.graph_client_secret,
            "code": code,
            "redirect_uri": s.microsoft_redirect_uri,
            "grant_type": "authorization_code",
            "scope": _SCOPES,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _TOKEN_URL.format(tenant_id=s.graph_tenant_id),
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("entra_token_exchange_failed status=%d body=%.300s", exc.code, error_body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Entra",
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("entra_token_exchange_network_error reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error contacting Entra token endpoint",
        ) from exc


def _fetch_userinfo(access_token: str) -> dict[str, Any]:
    req = urllib.request.Request(_USERINFO_URL, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("entra_userinfo_failed status=%d body=%.300s", exc.code, error_body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from Microsoft Graph",
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("entra_userinfo_network_error reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error contacting Microsoft Graph",
        ) from exc


@router.get("/callback")
def microsoft_callback(
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
            url=f"{s.microsoft_post_logout_url}?error=entra_denied",
            status_code=302,
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code"
        )

    if not _verify_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state parameter"
        )

    token_data = _exchange_code(code)
    ms_access_token: str = token_data.get("access_token", "")
    if not ms_access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="No access_token in Entra response"
        )

    userinfo = _fetch_userinfo(ms_access_token)
    email: str = (userinfo.get("mail") or userinfo.get("userPrincipalName") or "").lower().strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No email in Microsoft profile"
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)
    if user is None:
        logger.warning("entra_login_no_matching_user email=%s", email)
        return RedirectResponse(
            url=f"{s.microsoft_post_logout_url}?error=no_account",
            status_code=302,
        )

    jwt_token = create_access_token(str(user.id), str(user.tenant_id), user.role or "")
    logger.info("entra_login_success user_id=%s email=%s", user.id, email)

    redirect_url = f"{s.microsoft_post_login_url}?token={jwt_token}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/logout")
def microsoft_logout() -> RedirectResponse:
    _check_entra_configured()
    s = get_settings()
    params = {
        "post_logout_redirect_uri": s.microsoft_post_logout_url,
    }
    url = _LOGOUT_URL.format(tenant_id=s.graph_tenant_id) + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=url, status_code=302)
