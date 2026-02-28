from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from boto3.dynamodb import conditions as ddb_conditions

logger = logging.getLogger(__name__)

# ── Status machine ─────────────────────────────────────────────────────────────
# Only forward or lateral transitions are allowed.
PAYMENT_STATUS_MAP: dict[str, str] = {
    "checkout.session.completed": "paid",
    "payment_intent.succeeded":   "paid",
    "payment_intent.payment_failed": "failed",
    "charge.refunded":            "refunded",
    "charge.dispute.created":     "disputed",
}

STATUS_RANK: dict[str, int] = {
    "pending":  0,
    "failed":  10,
    "paid":    50,
    "refunded": 60,
    "disputed": 70,
}


def _rank(s: str) -> int:
    return STATUS_RANK.get(s, 0)


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
            "STRIPE_EVENTS_TABLE / TENANTS_TABLE env vars are set."
        )
    return _get_ddb().Table(name)


STATEMENTS_TABLE     = os.environ.get("STATEMENTS_TABLE") or ""
STRIPE_EVENTS_TABLE  = os.environ.get("STRIPE_EVENTS_TABLE") or ""
TENANTS_TABLE        = os.environ.get("TENANTS_TABLE") or ""


# ── Core worker logic ──────────────────────────────────────────────────────────

def process_stripe_event(message_body: dict[str, Any]) -> None:
    event_id:            str = message_body["event_id"]
    event_type:          str = message_body["event_type"]
    connected_account_id = message_body.get("connected_account_id")
    payload:             dict[str, Any] = message_body.get("payload", {})
    correlation_id:      str = message_body.get("correlation_id", "")

    logger.info(
        "stripe_worker_processing event_id=%s event_type=%s account=%s correlation_id=%s",
        event_id, event_type, connected_account_id, correlation_id,
    )

    # Idempotency
    events_table = _table(STRIPE_EVENTS_TABLE)
    existing = events_table.get_item(Key={"event_id": event_id}).get("Item")
    if existing and existing.get("processed"):
        logger.info("stripe_worker_duplicate event_id=%s", event_id)
        return

    events_table.put_item(Item={
        "event_id": event_id,
        "event_type": event_type,
        "connected_account_id": connected_account_id or "",
        "payload": json.dumps(payload, default=str),
        "correlation_id": correlation_id,
        "processed": False,
    })

    new_payment_status = PAYMENT_STATUS_MAP.get(event_type)
    if not new_payment_status:
        logger.info("stripe_worker_unhandled_event_type event_type=%s", event_type)
        _mark_processed(events_table, event_id)
        return

    # Extract statement_id from metadata depending on event type
    statement_id = _extract_statement_id(event_type, payload)
    if not statement_id:
        logger.warning(
            "stripe_worker_no_statement_id event_id=%s event_type=%s", event_id, event_type
        )
        _mark_processed(events_table, event_id)
        return

    # Route to correct tenant via connected account
    tenant_id = _resolve_tenant(connected_account_id) if connected_account_id else None

    _update_statement_payment_status(
        statement_id=statement_id,
        new_status=new_payment_status,
        event_type=event_type,
        event_id=event_id,
        payload=payload,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    _mark_processed(events_table, event_id)
    logger.info("stripe_worker_done event_id=%s new_status=%s", event_id, new_payment_status)


def _extract_statement_id(event_type: str, payload: dict[str, Any]) -> str | None:
    data_obj = payload.get("data", {}).get("object", {})
    metadata: dict[str, str] = data_obj.get("metadata", {})
    if metadata.get("statement_id"):
        return metadata["statement_id"]
    if event_type in ("charge.refunded", "charge.dispute.created"):
        pi_meta = data_obj.get("payment_intent", {})
        if isinstance(pi_meta, dict):
            return pi_meta.get("metadata", {}).get("statement_id")
    return None


def _resolve_tenant(connected_account_id: str) -> str | None:
    table = _table(TENANTS_TABLE)
    resp = table.query(
        IndexName="stripe_connected_account_id-index",
        KeyConditionExpression=ddb_conditions.Key(
            "stripe_connected_account_id"
        ).eq(connected_account_id),
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0].get("tenant_id") if items else None


def _update_statement_payment_status(
    *,
    statement_id: str,
    new_status: str,
    event_type: str,
    event_id: str,
    payload: dict[str, Any],
    tenant_id: str | None,
    correlation_id: str,
) -> None:
    table = _table(STATEMENTS_TABLE)
    item = table.get_item(Key={"statement_id": statement_id}).get("Item")
    if not item:
        logger.warning("stripe_worker_statement_not_found statement_id=%s", statement_id)
        return

    current_status: str = item.get("payment_status", "pending")
    if _rank(new_status) <= _rank(current_status) and current_status != "failed":
        logger.info(
            "stripe_worker_status_skip statement_id=%s current=%s new=%s",
            statement_id, current_status, new_status,
        )
        return

    update_expr = (
        "SET payment_status = :s, "
        "payment_last_event_type = :et, "
        "payment_last_event_id = :eid, "
        "payment_updated_at = :now"
    )
    expr_vals: dict[str, Any] = {
        ":s":   new_status,
        ":et":  event_type,
        ":eid": event_id,
        ":now": _utcnow(),
        ":cs":  current_status,
    }

    try:
        table.update_item(
            Key={"statement_id": statement_id},
            UpdateExpression=update_expr,
            ConditionExpression="payment_status = :cs OR attribute_not_exists(payment_status)",
            ExpressionAttributeValues=expr_vals,
        )
        logger.info(
            "stripe_worker_status_updated statement_id=%s %s -> %s correlation_id=%s",
            statement_id, current_status, new_status, correlation_id,
        )
    except Exception as exc:
        logger.error(
            "stripe_worker_conditional_write_failed statement_id=%s error=%s",
            statement_id, exc,
        )


def _mark_processed(table: Any, event_id: str) -> None:
    table.update_item(
        Key={"event_id": event_id},
        UpdateExpression="SET processed = :t",
        ExpressionAttributeValues={":t": True},
    )


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── Lambda handler ────────────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_stripe_event(body)
        except Exception as exc:
            logger.exception(
                "stripe_worker_record_failed message_id=%s error=%s",
                record.get("messageId", ""), exc,
            )
            raise
