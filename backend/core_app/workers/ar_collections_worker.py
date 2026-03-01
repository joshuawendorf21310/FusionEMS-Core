from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    _engine = create_engine(DATABASE_URL) if DATABASE_URL else None
    _Session = sessionmaker(bind=_engine) if _engine else None
except Exception:
    _engine = None
    _Session = None

DUNNING_DAYS = [0, 15, 30, 45, 60]
PLACEMENT_THRESHOLD_DAYS = 90


def lambda_handler(event: dict, context: Any) -> dict:
    results = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            job_type = body.get("job_type", "")
            correlation_id = body.get("correlation_id") or str(uuid.uuid4())
            if job_type == "ar.statement.schedule":
                results.append(_run_statement_schedule(body, correlation_id))
            elif job_type == "ar.payment.post":
                results.append(_post_payment(body, correlation_id))
            elif job_type == "ar.placement.generate_export":
                results.append(_generate_placement(body, correlation_id))
            elif job_type == "ar.status.import_parse":
                results.append(_import_status(body, correlation_id))
            else:
                logger.warning("ar_worker_unknown_job job_type=%s", job_type)
        except Exception as exc:
            logger.exception("ar_worker_error error=%s", exc)
    return {"statusCode": 200, "results": results}


def _run_statement_schedule(body: dict, correlation_id: str) -> dict:
    if not _Session:
        return {"error": "no_db"}
    db = _Session()
    try:
        import json as _json

        from sqlalchemy import text

        rows = db.execute(
            text(
                "SELECT id, tenant_id, data FROM ar_accounts WHERE data->>'status' NOT IN ('closed','placed','dispute')"
            )
        ).fetchall()
        queued = 0
        for row in rows:
            data = row[2] if isinstance(row[2], dict) else _json.loads(row[2])
            if (data.get("balance_cents") or 0) <= 0:
                continue
            stmt_id = uuid.uuid4()
            db.execute(
                text("""
                INSERT INTO ar_statements (id, tenant_id, version, data, created_at, updated_at)
                VALUES (:id, :tid, 1, :data, now(), now())
            """),
                {
                    "id": str(stmt_id),
                    "tid": str(row[1]),
                    "data": _json.dumps(
                        {
                            "account_id": str(row[0]),
                            "statement_cycle": (data.get("dunning_cycle") or 0) + 1,
                            "delivery_method": "mail",
                            "status": "queued",
                            "balance_cents": data.get("balance_cents", 0),
                        }
                    ),
                },
            )
            queued += 1
        db.commit()
        logger.info(
            "ar_statement_schedule_done queued=%d correlation_id=%s", queued, correlation_id
        )
        return {"queued": queued}
    except Exception as exc:
        db.rollback()
        logger.error("ar_statement_schedule_error error=%s correlation_id=%s", exc, correlation_id)
        return {"error": str(exc)}
    finally:
        db.close()


def _post_payment(body: dict, correlation_id: str) -> dict:
    if not _Session:
        return {"error": "no_db"}
    account_id = body.get("account_id", "")
    amount_cents = int(body.get("amount_cents", 0))
    if not account_id or amount_cents <= 0:
        return {"error": "invalid_params"}
    db = _Session()
    try:
        import json as _json

        from sqlalchemy import text

        row = db.execute(
            text("SELECT id, tenant_id, version, data FROM ar_accounts WHERE id = :id"),
            {"id": account_id},
        ).fetchone()
        if not row:
            return {"error": "account_not_found"}
        data = row[3] if isinstance(row[3], dict) else _json.loads(row[3])
        new_balance = max(0, (data.get("balance_cents") or 0) - amount_cents)
        data["balance_cents"] = new_balance
        if new_balance == 0:
            data["status"] = "closed"
        payment_id = uuid.uuid4()
        db.execute(
            text("""
            INSERT INTO ar_payments (id, tenant_id, version, data, created_at, updated_at)
            VALUES (:id, :tid, 1, :data, now(), now())
        """),
            {
                "id": str(payment_id),
                "tid": str(row[1]),
                "data": _json.dumps(
                    {
                        "account_id": account_id,
                        "amount_cents": amount_cents,
                        "method": body.get("method", "card"),
                        "processor_ref": body.get("processor_ref"),
                        "posted_at": datetime.now(UTC).isoformat(),
                    }
                ),
            },
        )
        db.execute(
            text("""
            UPDATE ar_accounts SET data = :data, version = version + 1, updated_at = now() WHERE id = :id
        """),
            {"data": _json.dumps(data), "id": account_id},
        )
        db.commit()
        return {"payment_id": str(payment_id), "new_balance": new_balance}
    except Exception as exc:
        db.rollback()
        logger.error("ar_payment_post_error error=%s correlation_id=%s", exc, correlation_id)
        return {"error": str(exc)}
    finally:
        db.close()


def _generate_placement(body: dict, correlation_id: str) -> dict:
    logger.info("ar_placement_generate correlation_id=%s", correlation_id)
    return {"status": "deferred_to_api"}


def _import_status(body: dict, correlation_id: str) -> dict:
    logger.info("ar_status_import s3_key=%s correlation_id=%s", body.get("s3_key"), correlation_id)
    return {"status": "deferred_to_api"}
