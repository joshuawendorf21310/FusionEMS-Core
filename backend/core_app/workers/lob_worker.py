from __future__ import annotations

import json
import logging
import os
from datetime import UTC
from typing import Any

import boto3

logger = logging.getLogger(__name__)

# ── Statement status machine ──────────────────────────────────────────────────
# Allowed forward transitions only; out-of-order events are dropped gracefully.
LOB_STATUS_TRANSITIONS: dict[str, str] = {
    "letter.created":             "lob_created",
    "letter.rendered_pdf":        "lob_rendered",
    "letter.rendered_thumbnails": "lob_rendered",
    "letter.billed":              "lob_billed",
    "letter.viewed":              "lob_viewed",
    "letter.failed":              "lob_failed",
    "letter.rejected":            "lob_rejected",
    "letter.deleted":             "lob_deleted",
    "address.created":            None,
    "address.deleted":            None,
}

STATUS_RANK: dict[str, int] = {
    "lob_created":   10,
    "lob_rendered":  20,
    "lob_billed":    30,
    "lob_viewed":    40,
    "lob_failed":     5,
    "lob_rejected":   5,
    "lob_deleted":    5,
    "paid":         100,
    "refunded":     110,
    "disputed":     120,
}


def _rank(status: str) -> int:
    return STATUS_RANK.get(status, 0)


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

_ddb: Any = None


def _get_ddb():
    global _ddb
    if _ddb is None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            raise RuntimeError(
                "AWS_REGION environment variable is not set. "
                "Set it to the region where your DynamoDB tables are deployed."
            )
        _ddb = boto3.resource("dynamodb", region_name=region)
    return _ddb


def _table(name: str):
    if not name:
        raise RuntimeError(
            "DynamoDB table name is empty — ensure STATEMENTS_TABLE / "
            "LOB_EVENTS_TABLE env vars are set."
        )
    return _get_ddb().Table(name)


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"{name} environment variable is not set. "
            "All DynamoDB table names must be explicitly configured per environment."
        )
    return val


STATEMENTS_TABLE    = os.environ.get("STATEMENTS_TABLE") or ""
LOB_EVENTS_TABLE    = os.environ.get("LOB_EVENTS_TABLE") or ""


# ── Core worker logic ─────────────────────────────────────────────────────────

def process_lob_event(message_body: dict[str, Any]) -> None:
    event_id:    str = message_body["event_id"]
    event_type:  str = message_body["event_type"]
    payload:     dict[str, Any] = message_body.get("payload", {})
    correlation_id: str = message_body.get("correlation_id", "")

    logger.info(
        "lob_worker_processing event_id=%s event_type=%s correlation_id=%s",
        event_id, event_type, correlation_id,
    )

    # Idempotency: check DynamoDB lob_events table
    events_table = _table(LOB_EVENTS_TABLE)
    existing = events_table.get_item(Key={"event_id": event_id}).get("Item")
    if existing and existing.get("processed"):
        logger.info("lob_worker_duplicate event_id=%s", event_id)
        return

    events_table.put_item(Item={
        "event_id": event_id,
        "event_type": event_type,
        "payload": json.dumps(payload, default=str),
        "correlation_id": correlation_id,
        "processed": False,
    })

    # Extract the Lob letter id and statement_id from payload
    body = payload.get("body") or payload
    lob_letter_id: str | None = body.get("id")
    metadata: dict[str, str] = body.get("metadata", {})
    statement_id: str | None = metadata.get("statement_id")

    new_status = LOB_STATUS_TRANSITIONS.get(event_type)

    if statement_id and new_status:
        _update_statement_lob_status(
            statement_id=statement_id,
            lob_letter_id=lob_letter_id,
            new_status=new_status,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )

    if event_type == "letter.rendered_pdf":
        _attach_rendered_pdf(statement_id, body, correlation_id)

    if event_type == "letter.rendered_thumbnails":
        _attach_thumbnails(statement_id, body, correlation_id)

    events_table.update_item(
        Key={"event_id": event_id},
        UpdateExpression="SET processed = :t",
        ExpressionAttributeValues={":t": True},
    )
    logger.info("lob_worker_done event_id=%s event_type=%s", event_id, event_type)


def _update_statement_lob_status(
    *,
    statement_id: str,
    lob_letter_id: str | None,
    new_status: str,
    event_type: str,
    payload: dict[str, Any],
    correlation_id: str,
) -> None:
    table = _table(STATEMENTS_TABLE)
    item = table.get_item(Key={"statement_id": statement_id}).get("Item")

    if not item:
        logger.warning("lob_worker_statement_not_found statement_id=%s", statement_id)
        return

    current_status: str = item.get("lob_status", "")
    if _rank(new_status) <= _rank(current_status):
        logger.info(
            "lob_worker_status_skip statement_id=%s current=%s new=%s",
            statement_id, current_status, new_status,
        )
        return

    table.update_item(
        Key={"statement_id": statement_id},
        UpdateExpression=(
            "SET lob_status = :s, lob_letter_id = :lid, "
            "lob_last_event_type = :et, lob_last_event_at = :now"
        ),
        ConditionExpression="attribute_not_exists(lob_status) OR lob_status = :cs",
        ExpressionAttributeValues={
            ":s":   new_status,
            ":lid": lob_letter_id or item.get("lob_letter_id", ""),
            ":et":  event_type,
            ":now": _utcnow(),
            ":cs":  current_status,
        },
    )
    logger.info(
        "lob_worker_status_updated statement_id=%s %s -> %s correlation_id=%s",
        statement_id, current_status, new_status, correlation_id,
    )


def _attach_rendered_pdf(
    statement_id: str | None,
    body: dict[str, Any],
    correlation_id: str,
) -> None:
    if not statement_id:
        return
    pdf_url: str | None = body.get("url") or body.get("thumbnails", [{}])[0].get("large")
    if not pdf_url:
        return
    table = _table(STATEMENTS_TABLE)
    table.update_item(
        Key={"statement_id": statement_id},
        UpdateExpression="SET lob_rendered_pdf_url = :u, lob_rendered_at = :t",
        ExpressionAttributeValues={":u": pdf_url, ":t": _utcnow()},
    )
    logger.info(
        "lob_worker_pdf_attached statement_id=%s url=%.40s correlation_id=%s",
        statement_id, pdf_url, correlation_id,
    )


def _attach_thumbnails(
    statement_id: str | None,
    body: dict[str, Any],
    correlation_id: str,
) -> None:
    if not statement_id:
        return
    thumbnails = body.get("thumbnails", [])
    if not thumbnails:
        return
    table = _table(STATEMENTS_TABLE)
    table.update_item(
        Key={"statement_id": statement_id},
        UpdateExpression="SET lob_thumbnails = :t, lob_thumbnails_at = :at",
        ExpressionAttributeValues={":t": thumbnails, ":at": _utcnow()},
    )
    logger.info(
        "lob_worker_thumbnails_attached statement_id=%s count=%d correlation_id=%s",
        statement_id, len(thumbnails), correlation_id,
    )


def _utcnow() -> str:
    from datetime import datetime
    return datetime.now(UTC).isoformat()


# ── Lambda handler ────────────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_lob_event(body)
        except Exception as exc:
            logger.exception(
                "lob_worker_record_failed message_id=%s error=%s",
                record.get("messageId", ""), exc,
            )
            raise
