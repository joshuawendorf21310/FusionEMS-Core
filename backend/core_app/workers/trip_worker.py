"""TRIP (WI) SQS Lambda worker.

Handles background jobs enqueued by trip_router:
  trip.debt.candidate_build    — re-evaluate debts and mark candidates
  trip.export.generate_xml     — generate XML export and upload to S3
  trip.posting.apply_payments  — parse posting file and update debt statuses
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    _engine = create_engine(DATABASE_URL) if DATABASE_URL else None
    _Session = sessionmaker(bind=_engine) if _engine else None
except Exception:
    _engine = None
    _Session = None


def _get_db():
    if _Session is None:
        raise RuntimeError("Database not configured — DATABASE_URL missing")
    return _Session()


def _handle_debt_candidate_build(body: dict, correlation_id: str) -> dict:
    """Re-score existing trip_debts and mark eligible ones as 'candidate'."""
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        raise ValueError("tenant_id required")

    MIN_BALANCE = int(os.environ.get("TRIP_MIN_BALANCE_CENTS", "2500"))
    REQUIRED_FIELDS = ("debtor_name", "identifier_type", "identifier_value_encrypted")

    db = _get_db()
    try:
        rows = (
            db.execute(
                text("""
                SELECT id, version, data FROM trip_debts
                WHERE tenant_id = :tid AND deleted_at IS NULL
                  AND (data->>'status' IS NULL OR data->>'status' NOT IN ('exported','resolved','cancelled'))
            """),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )

        updated = 0
        for row in rows:
            data = dict(row["data"] or {})
            balance = int(data.get("balance_cents", 0))
            has_required = all(data.get(f) for f in REQUIRED_FIELDS)
            is_eligible = (
                has_required
                and balance >= MIN_BALANCE
                and data.get("identifier_type") in ("ssn", "dob_name", "account_number")
            )
            new_status = "candidate" if is_eligible else "ineligible"
            if data.get("status") == new_status:
                continue
            data["status"] = new_status
            db.execute(
                text("""
                    UPDATE trip_debts
                    SET data = CAST(:data AS jsonb), version = version + 1, updated_at = now()
                    WHERE id = :id AND version = :ver AND tenant_id = :tid
                """),
                {
                    "data": json.dumps(data),
                    "id": str(row["id"]),
                    "ver": row["version"],
                    "tid": tenant_id,
                },
            )
            updated += 1

        db.commit()
        logger.info(
            "trip_debt_candidate_build tenant=%s updated=%d correlation_id=%s",
            tenant_id,
            updated,
            correlation_id,
        )
        return {"status": "ok", "updated": updated}
    finally:
        db.close()


def _handle_export_generate_xml(body: dict, correlation_id: str) -> dict:
    """Generate TRIP XML export and upload to S3."""
    tenant_id = body.get("tenant_id")
    export_id = body.get("export_id")
    if not tenant_id or not export_id:
        raise ValueError("tenant_id and export_id required")

    db = _get_db()
    try:
        rows = (
            db.execute(
                text("""
                SELECT id, version, data FROM trip_debts
                WHERE tenant_id = :tid AND deleted_at IS NULL
                  AND data->>'status' = 'candidate'
            """),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )

        if not rows:
            logger.warning(
                "trip_export_generate_xml no candidates tenant=%s export_id=%s",
                tenant_id,
                export_id,
            )
            return {"status": "skipped", "reason": "no_candidates"}

        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<TRIPExport>"]
        for row in rows:
            d = row["data"] or {}
            lines.append(
                f'  <Debt id="{row["id"]}" balance="{d.get("balance_cents", 0)}" '
                f'debtor="{d.get("debtor_name", "")}" />'
            )
        lines.append("</TRIPExport>")
        xml_bytes = "\n".join(lines).encode("utf-8")

        s3_key = f"trip/exports/{tenant_id}/{export_id}.xml"
        bucket = os.environ.get("S3_BUCKET_EXPORTS", "")
        if bucket:
            try:
                import boto3

                s3 = boto3.client("s3")
                s3.put_object(
                    Bucket=bucket, Key=s3_key, Body=xml_bytes, ContentType="application/xml"
                )
                logger.info("trip_export_uploaded s3_key=%s", s3_key)
            except Exception as s3_err:
                logger.error("trip_export_s3_upload_failed s3_key=%s error=%s", s3_key, s3_err)

        db.execute(
            text("""
                UPDATE trip_exports
                SET data = data || CAST(:patch AS jsonb), version = version + 1, updated_at = now()
                WHERE tenant_id = :tid AND id = :eid
            """),
            {
                "patch": json.dumps(
                    {"status": "ready", "s3_xml_key": s3_key, "record_count": len(rows)}
                ),
                "tid": tenant_id,
                "eid": export_id,
            },
        )
        db.commit()
        return {"status": "ok", "s3_key": s3_key, "record_count": len(rows)}
    finally:
        db.close()


def _handle_posting_apply_payments(body: dict, correlation_id: str) -> dict:
    """Apply a TRIP posting file: mark matched debts as 'resolved' or 'partial'."""
    tenant_id = body.get("tenant_id")
    posting_id = body.get("posting_id")
    if not tenant_id or not posting_id:
        raise ValueError("tenant_id and posting_id required")

    db = _get_db()
    try:
        posting_row = (
            db.execute(
                text(
                    "SELECT data FROM trip_postings WHERE tenant_id = :tid AND id = :pid AND deleted_at IS NULL LIMIT 1"
                ),
                {"tid": tenant_id, "pid": posting_id},
            )
            .mappings()
            .first()
        )

        if not posting_row:
            raise ValueError(f"posting {posting_id} not found")

        postings_data = posting_row["data"] or {}
        payments: list[dict] = postings_data.get("payments", [])
        applied = 0

        for payment in payments:
            debt_id = payment.get("debt_id")
            paid_cents = int(payment.get("paid_cents", 0))
            if not debt_id:
                continue
            debt_row = (
                db.execute(
                    text(
                        "SELECT id, version, data FROM trip_debts WHERE tenant_id = :tid AND id = :did AND deleted_at IS NULL LIMIT 1"
                    ),
                    {"tid": tenant_id, "did": debt_id},
                )
                .mappings()
                .first()
            )
            if not debt_row:
                continue
            d = dict(debt_row["data"] or {})
            balance = int(d.get("balance_cents", 0))
            remaining = max(0, balance - paid_cents)
            d["balance_cents"] = remaining
            d["status"] = "resolved" if remaining == 0 else "partial"
            d["last_payment_cents"] = paid_cents
            db.execute(
                text("""
                    UPDATE trip_debts
                    SET data = CAST(:data AS jsonb), version = version + 1, updated_at = now()
                    WHERE id = :id AND version = :ver AND tenant_id = :tid
                """),
                {
                    "data": json.dumps(d),
                    "id": str(debt_row["id"]),
                    "ver": debt_row["version"],
                    "tid": tenant_id,
                },
            )
            applied += 1

        db.execute(
            text("""
                UPDATE trip_postings
                SET data = data || CAST(:patch AS jsonb), version = version + 1, updated_at = now()
                WHERE tenant_id = :tid AND id = :pid
            """),
            {
                "patch": json.dumps({"status": "applied", "applied_count": applied}),
                "tid": tenant_id,
                "pid": posting_id,
            },
        )
        db.commit()
        logger.info(
            "trip_posting_applied tenant=%s posting=%s applied=%d", tenant_id, posting_id, applied
        )
        return {"status": "ok", "applied": applied}
    finally:
        db.close()


def lambda_handler(event: dict, context: Any) -> dict:
    results = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            job_type = body.get("job_type", "")
            correlation_id = body.get("correlation_id") or str(uuid.uuid4())
            if job_type == "trip.debt.candidate_build":
                results.append(_handle_debt_candidate_build(body, correlation_id))
            elif job_type == "trip.export.generate_xml":
                results.append(_handle_export_generate_xml(body, correlation_id))
            elif job_type == "trip.posting.apply_payments":
                results.append(_handle_posting_apply_payments(body, correlation_id))
            else:
                logger.warning("trip_worker_unknown_job job_type=%s", job_type)
                results.append({"status": "unknown_job", "job": job_type})
        except Exception as exc:
            logger.exception("trip_worker_error error=%s", exc)
            results.append({"status": "error", "error": str(exc)})
    return {"statusCode": 200, "results": results}
