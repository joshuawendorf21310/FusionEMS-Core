"""Microsoft Graph application-permissions client (client credentials flow).

Architecture:
  - Acquires token via POST to /{tenant_id}/oauth2/v2.0/token with client_credentials grant
  - Caches token in-process; refreshes automatically before expiry
  - All calls reference the founder mailbox explicitly — never /me endpoints
  - Token is never persisted to database or exposed to the frontend
"""
from __future__ import annotations

import logging
import time
from typing import Any

import urllib.request
import urllib.parse
import urllib.error
import json as _json

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_SCOPE = "https://graph.microsoft.com/.default"

_REFRESH_BUFFER_SECONDS = 60


class GraphNotConfigured(Exception):
    pass


class GraphApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class _TokenCache:
    def __init__(self) -> None:
        self._access_token: str = ""
        self._expires_at: float = 0.0

    def is_valid(self) -> bool:
        return bool(self._access_token) and time.monotonic() < self._expires_at - _REFRESH_BUFFER_SECONDS

    def set(self, access_token: str, expires_in: int) -> None:
        self._access_token = access_token
        self._expires_at = time.monotonic() + expires_in

    @property
    def token(self) -> str:
        return self._access_token


_cache = _TokenCache()


def _acquire_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    url = _TOKEN_URL_TEMPLATE.format(tenant_id=tenant_id)
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": _SCOPE,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise GraphApiError(exc.code, f"token_acquisition_failed: {body_text}") from exc

    access_token: str = data.get("access_token", "")
    expires_in: int = int(data.get("expires_in", 3600))
    if not access_token:
        raise GraphApiError(500, "token_response_missing_access_token")
    _cache.set(access_token, expires_in)
    logger.info("graph_token_acquired expires_in=%d", expires_in)
    return access_token


def _get_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    if _cache.is_valid():
        return _cache.token
    return _acquire_token(tenant_id, client_id, client_secret)


def _graph_request(
    method: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    url = f"{_GRAPH_BASE}{path}"
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data: bytes | None = None
    if body is not None:
        data = _json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return _json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise GraphApiError(exc.code, body_text) from exc


def _graph_request_bytes(method: str, path: str, token: str) -> bytes:
    url = f"{_GRAPH_BASE}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise GraphApiError(exc.code, body_text) from exc


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, founder_email: str) -> None:
        if not all([tenant_id, client_id, client_secret, founder_email]):
            raise GraphNotConfigured("GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, and GRAPH_FOUNDER_EMAIL must all be set")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._founder_email = founder_email

    def _token(self) -> str:
        return _get_token(self._tenant_id, self._client_id, self._client_secret)

    def _mailbox(self) -> str:
        return self._founder_email

    def list_messages(self, top: int = 25, skip: int = 0, folder: str = "inbox") -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/mailFolders/{folder}/messages"
        params: dict[str, str] = {
            "$top": str(top),
            "$skip": str(skip),
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,hasAttachments",
        }
        return _graph_request("GET", path, token, params=params)

    def get_message(self, message_id: str) -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/messages/{message_id}"
        params = {"$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,body,hasAttachments"}
        return _graph_request("GET", path, token, params=params)

    def send_mail(self, to: list[str], subject: str, body_html: str, cc: list[str] | None = None) -> None:
        token = self._token()
        path = f"/users/{self._mailbox()}/sendMail"
        to_recipients = [{"emailAddress": {"address": addr}} for addr in to]
        cc_recipients = [{"emailAddress": {"address": addr}} for addr in (cc or [])]
        payload: dict[str, Any] = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": to_recipients,
            },
            "saveToSentItems": True,
        }
        if cc_recipients:
            payload["message"]["ccRecipients"] = cc_recipients
        _graph_request("POST", path, token, body=payload)

    def reply_to_message(self, message_id: str, comment_html: str) -> None:
        token = self._token()
        path = f"/users/{self._mailbox()}/messages/{message_id}/reply"
        payload = {"comment": comment_html}
        _graph_request("POST", path, token, body=payload)

    def list_attachments(self, message_id: str) -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/messages/{message_id}/attachments"
        params = {"$select": "id,name,contentType,size"}
        return _graph_request("GET", path, token, params=params)

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        token = self._token()
        path = f"/users/{self._mailbox()}/messages/{message_id}/attachments/{attachment_id}/$value"
        return _graph_request_bytes("GET", path, token)

    def list_drive_root(self) -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/drive/root/children"
        params = {"$select": "id,name,size,lastModifiedDateTime,file,folder,webUrl,@microsoft.graph.downloadUrl"}
        return _graph_request("GET", path, token, params=params)

    def list_drive_folder(self, item_id: str) -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/drive/items/{item_id}/children"
        params = {"$select": "id,name,size,lastModifiedDateTime,file,folder,webUrl,@microsoft.graph.downloadUrl"}
        return _graph_request("GET", path, token, params=params)

    def get_drive_item(self, item_id: str) -> dict[str, Any]:
        token = self._token()
        path = f"/users/{self._mailbox()}/drive/items/{item_id}"
        params = {"$select": "id,name,size,lastModifiedDateTime,file,folder,webUrl,@microsoft.graph.downloadUrl"}
        return _graph_request("GET", path, token, params=params)

    def get_drive_item_download_url(self, item_id: str) -> str:
        item = self.get_drive_item(item_id)
        url: str = item.get("@microsoft.graph.downloadUrl") or item.get("webUrl") or ""
        return url


def get_graph_client() -> GraphClient:
    from core_app.core.config import get_settings
    s = get_settings()
    if not all([s.graph_tenant_id, s.graph_client_id, s.graph_client_secret, s.graph_founder_email]):
        raise GraphNotConfigured(
            "Microsoft Graph is not configured. Set GRAPH_TENANT_ID, GRAPH_CLIENT_ID, "
            "GRAPH_CLIENT_SECRET, and GRAPH_FOUNDER_EMAIL."
        )
    return GraphClient(
        tenant_id=s.graph_tenant_id,
        client_id=s.graph_client_id,
        client_secret=s.graph_client_secret,
        founder_email=s.graph_founder_email,
    )
