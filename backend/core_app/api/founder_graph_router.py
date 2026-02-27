"""Founder-only Microsoft Graph API proxy.

All routes:
  - Require founder role (RBAC enforced by require_role("founder"))
  - Proxy all calls through backend — no Graph tokens exposed to frontend
  - Use application permissions (client credentials) via graph_service.GraphClient
  - Reference founder mailbox explicitly — /me endpoints are never used

Email endpoints:
  GET  /founder/graph/mail                          list inbox messages
  GET  /founder/graph/mail/{message_id}             message detail
  GET  /founder/graph/mail/{message_id}/attachments list attachments
  GET  /founder/graph/mail/{message_id}/attachments/{attachment_id}/download
  POST /founder/graph/mail/send                     send new email
  POST /founder/graph/mail/{message_id}/reply       reply to message

OneDrive endpoints:
  GET  /founder/graph/drive                         list root drive items
  GET  /founder/graph/drive/folders/{item_id}       list folder children
  GET  /founder/graph/drive/items/{item_id}         item metadata + webUrl
  GET  /founder/graph/drive/items/{item_id}/download-url  presigned/download URL
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from core_app.api.dependencies import require_role
from core_app.integrations.graph_service import (
    GraphApiError,
    GraphNotConfigured,
    get_graph_client,
)
from core_app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/founder/graph", tags=["Founder Graph"])

_FOUNDER = Depends(require_role("founder"))


def _raise_graph(exc: GraphApiError) -> None:
    raise HTTPException(status_code=exc.status if exc.status < 600 else 502, detail=exc.message)


def _raise_not_configured(exc: GraphNotConfigured) -> None:
    raise HTTPException(status_code=503, detail=str(exc))


class SendMailRequest(BaseModel):
    to: list[str]
    subject: str
    body_html: str
    cc: Optional[list[str]] = None


class ReplyRequest(BaseModel):
    comment_html: str


@router.get("/mail")
async def list_messages(
    folder: str = "inbox",
    top: int = 25,
    skip: int = 0,
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_mail_list user=%s folder=%s", current.user_id, folder)
    try:
        client = get_graph_client()
        return client.list_messages(top=min(top, 100), skip=skip, folder=folder)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/mail/{message_id}")
async def get_message(
    message_id: str,
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_mail_get user=%s message_id=%s", current.user_id, message_id)
    try:
        client = get_graph_client()
        return client.get_message(message_id)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/mail/{message_id}/attachments")
async def list_attachments(
    message_id: str,
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_mail_attachments user=%s message_id=%s", current.user_id, message_id)
    try:
        client = get_graph_client()
        return client.list_attachments(message_id)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/mail/{message_id}/attachments/{attachment_id}/download")
async def download_attachment(
    message_id: str,
    attachment_id: str,
    current: CurrentUser = _FOUNDER,
) -> Response:
    logger.info("graph_attachment_download user=%s message_id=%s attachment_id=%s",
                current.user_id, message_id, attachment_id)
    try:
        client = get_graph_client()
        raw = client.download_attachment(message_id, attachment_id)
        return Response(content=raw, media_type="application/octet-stream")
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return Response(content=b"", media_type="application/octet-stream")


@router.post("/mail/send", status_code=204)
async def send_mail(
    body: SendMailRequest,
    current: CurrentUser = _FOUNDER,
) -> None:
    logger.info("graph_send_mail user=%s to=%s", current.user_id, body.to)
    try:
        client = get_graph_client()
        client.send_mail(to=body.to, subject=body.subject, body_html=body.body_html, cc=body.cc)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)


@router.post("/mail/{message_id}/reply", status_code=204)
async def reply_to_message(
    message_id: str,
    body: ReplyRequest,
    current: CurrentUser = _FOUNDER,
) -> None:
    logger.info("graph_reply user=%s message_id=%s", current.user_id, message_id)
    try:
        client = get_graph_client()
        client.reply_to_message(message_id, body.comment_html)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)


@router.get("/drive")
async def list_drive_root(
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_drive_root user=%s", current.user_id)
    try:
        client = get_graph_client()
        return client.list_drive_root()
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/drive/folders/{item_id}")
async def list_drive_folder(
    item_id: str,
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_drive_folder user=%s item_id=%s", current.user_id, item_id)
    try:
        client = get_graph_client()
        return client.list_drive_folder(item_id)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/drive/items/{item_id}")
async def get_drive_item(
    item_id: str,
    current: CurrentUser = _FOUNDER,
) -> dict[str, Any]:
    logger.info("graph_drive_item user=%s item_id=%s", current.user_id, item_id)
    try:
        client = get_graph_client()
        return client.get_drive_item(item_id)
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}


@router.get("/drive/items/{item_id}/download-url")
async def get_drive_download_url(
    item_id: str,
    current: CurrentUser = _FOUNDER,
) -> dict[str, str]:
    logger.info("graph_drive_download_url user=%s item_id=%s", current.user_id, item_id)
    try:
        client = get_graph_client()
        url = client.get_drive_item_download_url(item_id)
        return {"download_url": url}
    except GraphNotConfigured as exc:
        _raise_not_configured(exc)
    except GraphApiError as exc:
        _raise_graph(exc)
    return {}
