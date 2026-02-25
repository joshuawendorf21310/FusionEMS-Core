import json
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import requests
from jose import jwt
from jose.exceptions import JWTError

from core_app.core.config import get_settings


@dataclass(frozen=True)
class CognitoClaims:
    sub: str
    email: str | None
    tenant_id: str | None
    role: str | None
    groups: list[str]


class CognitoAuthError(Exception):
    pass


@lru_cache(maxsize=1)
def _jwks() -> dict[str, Any]:
    settings = get_settings()
    if not settings.cognito_region or not settings.cognito_user_pool_id:
        raise CognitoAuthError("Cognito not configured (COGNITO_REGION/COGNITO_USER_POOL_ID).")
    url = f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _issuer() -> str:
    settings = get_settings()
    if settings.cognito_issuer:
        return settings.cognito_issuer
    if not settings.cognito_region or not settings.cognito_user_pool_id:
        raise CognitoAuthError("Cognito not configured (issuer).")
    return f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"


def verify_cognito_jwt(token: str) -> CognitoClaims:
    settings = get_settings()
    if not settings.cognito_app_client_id:
        raise CognitoAuthError("Cognito app client id not configured (COGNITO_APP_CLIENT_ID).")

    try:
        claims = jwt.decode(
            token,
            _jwks(),
            algorithms=["RS256"],
            audience=settings.cognito_app_client_id,
            issuer=_issuer(),
            options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
        )
    except JWTError as exc:
        raise CognitoAuthError(f"Invalid Cognito JWT: {exc}") from exc

    # Exp sanity (jose already verifies exp, but keep hard guardrails)
    exp = claims.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        raise CognitoAuthError("Token expired.")

    groups = claims.get("cognito:groups") or []
    if isinstance(groups, str):
        groups = [groups]

    # Custom claims: these should be added using Cognito Pre Token Generation trigger (recommended),
    # but we also tolerate a mapping by groups for early deployments.
    tenant_id = claims.get("custom:tenant_id") or claims.get("tenant_id")
    role = claims.get("custom:role") or claims.get("role")

    return CognitoClaims(
        sub=str(claims.get("sub")),
        email=claims.get("email"),
        tenant_id=str(tenant_id) if tenant_id else None,
        role=str(role) if role else None,
        groups=[str(g) for g in groups],
    )
