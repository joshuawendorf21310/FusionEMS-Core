"""Communications worker for Phase 5 (SMS/Email SQS background jobs).

Handles SMS (Telnyx) and Email (SES) dispatch as SQS-triggered Lambda/worker
tasks.  Each message type is processed idempotently and with explicit
tenant_id scoping for zero-trust isolation.

Message body schema
-------------------
{
    "message_id": "<idempotency key — use event/notification UUID>",
    "message_type": "sms" | "email",
    "tenant_id": "<UUID string>",
    "correlation_id": "<optional trace ID>",
    "payload": {
        // For SMS (message_type == "sms"):
        "to": "+1xxxxxxxxxx",
        "body": "Your appointment is confirmed.",

        // For email (message_type == "email"):
        "to": "recipient@example.com",
        "subject": "Your statement is ready",
        "html_body": "<p>...</p>",
        "text_body": "..."  // optional plain-text fallback
    }
}
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── Environment variables ─────────────────────────────────────────────────────

COMMS_EVENTS_TABLE: str = os.environ.get("COMMS_EVENTS_TABLE") or ""
SES_FROM_EMAIL: str = os.environ.get("SES_FROM_EMAIL") or "noreply@fusionemsquantum.com"
SES_CONFIGURATION_SET: str = os.environ.get("SES_CONFIGURATION_SET") or ""
TELNYX_API_KEY: str = os.environ.get("TELNYX_API_KEY") or ""
TELNYX_FROM_NUMBER: str = os.environ.get("TELNYX_FROM_NUMBER") or ""
TELNYX_MESSAGING_PROFILE_ID: str = os.environ.get("TELNYX_MESSAGING_PROFILE_ID") or ""
AWS_REGION: str = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or ""

# ── DynamoDB idempotency helpers ──────────────────────────────────────────────

_ddb: Any = None


def _get_ddb() -> Any:
    global _ddb
    if _ddb is None:
        if not AWS_REGION:
            raise RuntimeError(
                "AWS_REGION environment variable is not set. "
                "Set it to the region where your DynamoDB tables are deployed."
            )
        import boto3  # noqa: PLC0415

        _ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _ddb


def _comms_table() -> Any:
    if not COMMS_EVENTS_TABLE:
        raise RuntimeError(
            "COMMS_EVENTS_TABLE environment variable is not set. "
            "Configure the DynamoDB table name for communications idempotency."
        )
    return _get_ddb().Table(COMMS_EVENTS_TABLE)


def _is_duplicate(message_id: str) -> bool:
    """Return True if this message_id was already processed."""
    table = _comms_table()
    item = table.get_item(Key={"message_id": message_id}).get("Item")
    return bool(item and item.get("processed"))


def _mark_processing(message_id: str, message_type: str, tenant_id: str) -> None:
    table = _comms_table()
    table.put_item(
        Item={
            "message_id": message_id,
            "message_type": message_type,
            "tenant_id": tenant_id,
            "processed": False,
        }
    )


def _mark_processed(message_id: str, status: str = "sent") -> None:
    table = _comms_table()
    table.update_item(
        Key={"message_id": message_id},
        UpdateExpression="SET processed = :t, delivery_status = :s",
        ExpressionAttributeValues={":t": True, ":s": status},
    )


# ── SMS (Telnyx) ──────────────────────────────────────────────────────────────

def _send_sms(
    *,
    to: str,
    body: str,
    tenant_id: str,
    correlation_id: str,
) -> None:
    """Send an SMS via the Telnyx API.

    Uses environment-injected credentials; never accesses secrets directly.

    Args:
        to: E.164 recipient phone number.
        body: SMS message text (max 1600 chars; split into segments by Telnyx).
        tenant_id: Tenant UUID string for logging/audit.
        correlation_id: Trace ID.
    """
    if not TELNYX_API_KEY:
        raise RuntimeError(
            "TELNYX_API_KEY is not configured. "
            "Inject the secret from AWS Secrets Manager via the ECS task definition."
        )
    if not TELNYX_FROM_NUMBER:
        raise RuntimeError(
            "TELNYX_FROM_NUMBER is not configured. "
            "Set the TELNYX_FROM_NUMBER environment variable."
        )

    try:
        import telnyx  # noqa: PLC0415

        telnyx.api_key = TELNYX_API_KEY
        msg = telnyx.Message.create(
            **{
                "from": TELNYX_FROM_NUMBER,
                "to": to,
                "text": body,
                **(
                    {"messaging_profile_id": TELNYX_MESSAGING_PROFILE_ID}
                    if TELNYX_MESSAGING_PROFILE_ID
                    else {}
                ),
            }
        )
        logger.info(
            "communications_worker.sms_sent to=%s telnyx_id=%s tenant_id=%s correlation_id=%s",
            # Mask number for logs — only log last 4 digits
            f"***{to[-4:]}",
            getattr(msg, "id", "unknown"),
            tenant_id,
            correlation_id,
        )
    except ImportError as exc:
        raise RuntimeError(
            "telnyx Python package is not installed. Add 'telnyx' to requirements.txt."
        ) from exc


# ── Email (SES) ───────────────────────────────────────────────────────────────

def _send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None,
    tenant_id: str,
    correlation_id: str,
) -> None:
    """Send an email via Amazon SES.

    Uses boto3 with the ambient ECS task IAM role; no access keys stored in code.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        html_body: HTML content for the email body.
        text_body: Optional plain-text fallback.
        tenant_id: Tenant UUID string for logging/audit.
        correlation_id: Trace ID.
    """
    if not AWS_REGION:
        raise RuntimeError("AWS_REGION environment variable is not set.")

    import boto3  # noqa: PLC0415

    ses = boto3.client("ses", region_name=AWS_REGION)

    body_content: dict[str, Any] = {
        "Html": {"Data": html_body, "Charset": "UTF-8"},
    }
    if text_body:
        body_content["Text"] = {"Data": text_body, "Charset": "UTF-8"}

    send_kwargs: dict[str, Any] = {
        "Source": SES_FROM_EMAIL,
        "Destination": {"ToAddresses": [to]},
        "Message": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": body_content,
        },
    }
    if SES_CONFIGURATION_SET:
        send_kwargs["ConfigurationSetName"] = SES_CONFIGURATION_SET

    resp = ses.send_email(**send_kwargs)
    message_id = resp.get("MessageId", "unknown")
    logger.info(
        "communications_worker.email_sent to=%s ses_message_id=%s tenant_id=%s correlation_id=%s",
        to,
        message_id,
        tenant_id,
        correlation_id,
    )


# ── Core worker logic ─────────────────────────────────────────────────────────

def process_communications_message(message_body: dict[str, Any]) -> None:
    """Process a single communications message from the SQS queue.

    Supports two message types:
    - ``sms``: Dispatches a text message via Telnyx.
    - ``email``: Dispatches a transactional email via Amazon SES.

    Idempotency is enforced via DynamoDB (COMMS_EVENTS_TABLE).  Duplicate
    message_ids are silently dropped to prevent double-sends on SQS redelivery.

    Args:
        message_body: Parsed JSON body from the SQS record.
    """
    message_id: str = message_body["message_id"]
    message_type: str = message_body["message_type"]
    tenant_id: str = message_body.get("tenant_id", "")
    correlation_id: str = message_body.get("correlation_id", "")
    payload: dict[str, Any] = message_body.get("payload", {})

    logger.info(
        "communications_worker.processing message_id=%s type=%s tenant_id=%s correlation_id=%s",
        message_id,
        message_type,
        tenant_id,
        correlation_id,
    )

    # Idempotency check
    if _is_duplicate(message_id):
        logger.info("communications_worker.duplicate message_id=%s", message_id)
        return

    _mark_processing(message_id, message_type, tenant_id)

    try:
        if message_type == "sms":
            to: str = payload["to"]
            body: str = payload["body"]
            if not to or not body:
                raise ValueError("SMS payload must include 'to' and 'body' fields.")
            _send_sms(to=to, body=body, tenant_id=tenant_id, correlation_id=correlation_id)

        elif message_type == "email":
            to_email: str = payload["to"]
            subject: str = payload["subject"]
            html_body: str = payload["html_body"]
            text_body: str | None = payload.get("text_body")
            if not to_email or not subject or not html_body:
                raise ValueError("Email payload must include 'to', 'subject', and 'html_body'.")
            _send_email(
                to=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        else:
            logger.warning(
                "communications_worker.unknown_type message_type=%s message_id=%s",
                message_type,
                message_id,
            )
            _mark_processed(message_id, status="skipped_unknown_type")
            return

    except Exception as exc:
        logger.error(
            "communications_worker.send_failed message_id=%s type=%s error=%s",
            message_id,
            message_type,
            exc,
            exc_info=exc,
        )
        _mark_processed(message_id, status=f"failed: {exc!s}"[:512])
        raise

    _mark_processed(message_id, status="sent")
    logger.info(
        "communications_worker.done message_id=%s type=%s tenant_id=%s",
        message_id,
        message_type,
        tenant_id,
    )


# ── Lambda handler ────────────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> None:  # noqa: ARG001
    """AWS Lambda entry point for SQS-triggered communications dispatching."""
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_communications_message(body)
        except Exception as exc:
            logger.exception(
                "communications_worker.record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise
