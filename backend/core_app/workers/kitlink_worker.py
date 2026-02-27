from __future__ import annotations
import os
import json
import uuid
import boto3
from datetime import datetime, timezone, timedelta
from typing import Any

WORKER_TYPE = os.environ.get("KITLINK_WORKER_TYPE", "kitlink_ocr")

_s3 = boto3.client("s3")
_sqs = boto3.client("sqs")
_ssm = boto3.client("ssm")

BUCKET = os.environ.get("KITLINK_ARTIFACTS_BUCKET", "")
DB_URL = os.environ.get("DATABASE_URL", "")

QUEUE_URLS = {
    "kitlink_ocr": os.environ.get("KITLINK_OCR_QUEUE_URL", ""),
    "kitlink_stock_rebuild": os.environ.get("KITLINK_STOCK_REBUILD_QUEUE_URL", ""),
    "kitlink_expiration_sweep": os.environ.get("KITLINK_EXPIRATION_SWEEP_QUEUE_URL", ""),
    "kitlink_anomaly": os.environ.get("KITLINK_ANOMALY_QUEUE_URL", ""),
    "kitlink_pdf": os.environ.get("KITLINK_PDF_QUEUE_URL", ""),
    "compliance_pack_ingest": os.environ.get("KITLINK_PACK_INGEST_QUEUE_URL", ""),
}


def _db_conn():
    import psycopg2
    return psycopg2.connect(DB_URL)


def _enqueue(queue_key: str, body: dict):
    url = QUEUE_URLS.get(queue_key)
    if not url:
        return
    kwargs: dict = {"QueueUrl": url, "MessageBody": json.dumps(body)}
    if url.endswith(".fifo"):
        kwargs["MessageGroupId"] = body.get("tenant_id", "default")
        kwargs["MessageDeduplicationId"] = body.get("dedup_id", str(uuid.uuid4()))
    _sqs.send_message(**kwargs)


# ---------------------------------------------------------------------------
# OCR Worker
# ---------------------------------------------------------------------------

def handle_ocr(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    job_id = body.get("job_id")
    tenant_id = body.get("tenant_id")
    s3_key = body.get("s3_key")

    obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
    image_bytes = obj["Body"].read()

    import base64
    import openai

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    b64 = base64.b64encode(image_bytes).decode()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are an EMS supply inventory OCR assistant. "
                            "Extract item names, quantities, lot numbers, and expiration dates from this image. "
                            "Return a JSON array of objects: [{\"name\": str, \"qty\": int, \"lot\": str|null, \"expiry\": str|null}]. "
                            "Return only valid JSON, no markdown."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }
        ],
        max_tokens=1024,
    )

    raw_text = response.choices[0].message.content or "[]"
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = []

    conn = _db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE kitlink_ocr_jobs
        SET data = data || %s::jsonb,
            updated_at = now()
        WHERE data->>'job_id' = %s AND tenant_id = %s AND deleted_at IS NULL
        """,
        (
            json.dumps({"status": "needs_confirm", "ocr_result": parsed, "processed_at": datetime.now(timezone.utc).isoformat()}),
            job_id,
            tenant_id,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"job_id": job_id, "items_found": len(parsed)}


# ---------------------------------------------------------------------------
# Stock Rebuild Worker
# ---------------------------------------------------------------------------

def handle_stock_rebuild(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    tenant_id = body.get("tenant_id")
    location_id = body.get("location_id")

    conn = _db_conn()
    cur = conn.cursor()

    filter_clause = "AND tenant_id = %s AND deleted_at IS NULL"
    params: list = [tenant_id]
    if location_id:
        filter_clause += " AND data->>'location_id' = %s"
        params.append(location_id)

    cur.execute(
        f"""
        SELECT data->>'item_id' AS item_id,
               data->>'location_id' AS loc_id,
               SUM(CASE WHEN data->>'direction' = 'in' THEN (data->>'qty')::int ELSE 0 END) -
               SUM(CASE WHEN data->>'direction' = 'out' THEN (data->>'qty')::int ELSE 0 END) AS balance
        FROM inventory_transaction_lines
        WHERE {filter_clause.lstrip('AND ')}
        GROUP BY data->>'item_id', data->>'location_id'
        """,
        params,
    )
    rows = cur.fetchall()

    rebuilt = 0
    for item_id, loc_id, balance in rows:
        if not item_id:
            continue
        cur.execute(
            """
            SELECT id FROM stock_balances
            WHERE tenant_id = %s
              AND data->>'item_id' = %s
              AND data->>'location_id' = %s
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (tenant_id, item_id, loc_id or ""),
        )
        existing = cur.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            cur.execute(
                """
                UPDATE stock_balances
                SET data = data || jsonb_build_object('current_qty', %s, 'rebuilt_at', %s),
                    updated_at = now()
                WHERE id = %s
                """,
                (int(balance or 0), now, existing[0]),
            )
        else:
            cur.execute(
                """
                INSERT INTO stock_balances (id, tenant_id, version, data, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, 1,
                        jsonb_build_object('item_id', %s, 'location_id', %s, 'current_qty', %s, 'rebuilt_at', %s),
                        now(), now())
                """,
                (tenant_id, item_id, loc_id or "", int(balance or 0), now),
            )
        rebuilt += 1

    conn.commit()
    cur.close()
    conn.close()
    return {"tenant_id": tenant_id, "balances_rebuilt": rebuilt}


# ---------------------------------------------------------------------------
# Expiration Sweep Worker
# ---------------------------------------------------------------------------

def handle_expiration_sweep(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    days_ahead = int(body.get("days_ahead", 30))
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()

    conn = _db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tenant_id, id, data
        FROM stock_balances
        WHERE deleted_at IS NULL
          AND data->>'expiration_date' IS NOT NULL
          AND data->>'expiration_date' <= %s
        """,
        (cutoff,),
    )
    rows = cur.fetchall()

    alerts = []
    for tenant_id, row_id, data in rows:
        if isinstance(data, str):
            data = json.loads(data)
        alerts.append({
            "tenant_id": str(tenant_id),
            "balance_id": str(row_id),
            "item_id": data.get("item_id"),
            "expiration_date": data.get("expiration_date"),
            "current_qty": data.get("current_qty"),
        })
        _enqueue("kitlink_anomaly", {
            "tenant_id": str(tenant_id),
            "event_type": "expiring_soon",
            "balance_id": str(row_id),
            "item_id": data.get("item_id"),
            "expiration_date": data.get("expiration_date"),
            "dedup_id": f"exp-sweep-{row_id}",
        })

    cur.close()
    conn.close()
    return {"sweep_date": datetime.now(timezone.utc).isoformat(), "expiring_count": len(alerts)}


# ---------------------------------------------------------------------------
# Anomaly Detection Worker
# ---------------------------------------------------------------------------

def handle_anomaly(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    tenant_id = body.get("tenant_id")
    event_type = body.get("event_type")

    flags = []

    if event_type == "narc_count_mismatch":
        delta = abs(body.get("delta", 0))
        severity = "critical" if delta > 1 else "warning"
        flags.append({
            "rule": "NARC_COUNT_MISMATCH",
            "severity": severity,
            "detail": f"Narcotics count mismatch: delta={body.get('delta')}",
        })

    if event_type == "missing_witness":
        flags.append({
            "rule": "MISSING_WITNESS",
            "severity": "critical",
            "detail": "Waste event recorded without required witness",
        })

    if event_type == "seal_inconsistency":
        flags.append({
            "rule": "SEAL_INCONSISTENCY",
            "severity": "warning",
            "detail": "Seal code mismatch between scan and record",
        })

    if event_type == "expiring_soon":
        flags.append({
            "rule": "EXPIRING_SOON",
            "severity": "info",
            "detail": f"Item {body.get('item_id')} expires {body.get('expiration_date')}",
        })

    if not flags:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        prompt = (
            "You are an EMS narcotics chain-of-custody anomaly detector. "
            "Review this event and identify if anything needs human review. "
            "Rules: only flag 'needs_review' if there is a genuine discrepancy. Never accuse. "
            f"Event: {json.dumps(body)}. "
            "Respond with JSON: {\"flag\": bool, \"reason\": str}."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        try:
            ai_result = json.loads(resp.choices[0].message.content or "{}")
            if ai_result.get("flag"):
                flags.append({"rule": "AI_REVIEW", "severity": "info", "detail": ai_result.get("reason", "")})
        except Exception:
            pass

    if flags:
        conn = _db_conn()
        cur = conn.cursor()
        for flag in flags:
            cur.execute(
                """
                INSERT INTO kitlink_anomaly_flags (id, tenant_id, version, data, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, 1, %s::jsonb, now(), now())
                """,
                (tenant_id, json.dumps({**flag, "event": body, "flagged_at": datetime.now(timezone.utc).isoformat()})),
            )
        conn.commit()
        cur.close()
        conn.close()

    return {"event_type": event_type, "flags_created": len(flags)}


# ---------------------------------------------------------------------------
# PDF Worker
# ---------------------------------------------------------------------------

def handle_pdf(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    tenant_id = body.get("tenant_id")
    doc_type = body.get("doc_type", "inspection_report")
    entity_id = body.get("entity_id")

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>FusionEMS KitLink Report</title></head>
<body>
<h1>KitLink {doc_type.replace('_', ' ').title()}</h1>
<p>Tenant: {tenant_id}</p>
<p>Entity: {entity_id}</p>
<p>Generated: {datetime.now(timezone.utc).isoformat()}</p>
<p>Report Type: {doc_type}</p>
</body>
</html>"""

    s3_key = f"kitlink/exports/{tenant_id}/{doc_type}/{entity_id}.pdf"
    _s3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=html_content.encode(),
        ContentType="text/html",
        Metadata={"tenant_id": tenant_id, "doc_type": doc_type},
    )

    return {"s3_key": s3_key, "doc_type": doc_type, "entity_id": entity_id}


# ---------------------------------------------------------------------------
# Compliance Pack Ingest Worker
# ---------------------------------------------------------------------------

def handle_compliance_pack_ingest(record: dict) -> dict:
    body = json.loads(record.get("body", "{}"))
    pack_key = body.get("pack_key")
    s3_key = body.get("s3_key") or f"compliance/packs/{pack_key}.json"

    obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
    pack_data = json.loads(obj["Body"].read())

    param_path = f"/{os.environ.get('APP_NAME', 'fusionems')}/{os.environ.get('STAGE', 'prod')}/kitlink/packs/{pack_key}"
    _ssm.put_parameter(
        Name=param_path,
        Value=s3_key,
        Type="String",
        Overwrite=True,
        Description=f"KitLink compliance pack S3 key: {pack_key}",
    )

    return {"pack_key": pack_key, "s3_key": s3_key, "rules_count": len(pack_data.get("rules", []))}


# ---------------------------------------------------------------------------
# Lambda dispatcher
# ---------------------------------------------------------------------------

_HANDLERS = {
    "kitlink_ocr": handle_ocr,
    "kitlink_stock_rebuild": handle_stock_rebuild,
    "kitlink_expiration_sweep": handle_expiration_sweep,
    "kitlink_anomaly": handle_anomaly,
    "kitlink_pdf": handle_pdf,
    "compliance_pack_ingest": handle_compliance_pack_ingest,
}


def lambda_handler(event: dict, context: Any) -> dict:
    handler = _HANDLERS.get(WORKER_TYPE)
    if not handler:
        raise ValueError(f"Unknown KITLINK_WORKER_TYPE: {WORKER_TYPE}")

    records = event.get("Records", [event])
    results = []
    for record in records:
        try:
            result = handler(record)
            results.append({"status": "ok", "result": result})
        except Exception as exc:
            results.append({"status": "error", "error": str(exc)})

    return {"batchItemFailures": [], "results": results}
