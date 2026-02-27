from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import urllib.request
import uuid
import zipfile
from typing import Any

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core_app.documents.s3_storage import put_bytes

logger = logging.getLogger(__name__)
PACK_S3_PREFIX = "neris/packs"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_engine = create_engine(DATABASE_URL) if DATABASE_URL else None
_Session = sessionmaker(bind=_engine) if _engine else None


def lambda_handler(event: dict, context: Any) -> dict:
    results = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            correlation_id = body.get("correlation_id") or str(uuid.uuid4())
            job_type = body.get("job_type", "")
            if job_type == "neris.pack.import":
                results.append(process_pack_import(body, correlation_id))
            elif job_type == "neris.pack.compile_rules":
                results.append(process_pack_compile(body, correlation_id))
            else:
                logger.warning("neris_pack_unknown_job_type job_type=%s correlation_id=%s", job_type, correlation_id)
        except Exception as exc:
            logger.exception("neris_pack_worker_error error=%s", exc)
    return {"statusCode": 200, "results": results}


def process_pack_import(body: dict, correlation_id: str) -> dict:
    pack_id = body.get("pack_id", "")
    repo = body.get("repo", "ulfsri/neris-framework")
    ref = body.get("ref", "main")
    tenant_id = body.get("tenant_id", "")
    actor_user_id = body.get("actor_user_id", "")

    logger.info("neris_pack_import_start pack_id=%s repo=%s ref=%s correlation_id=%s", pack_id, repo, ref, correlation_id)

    if not _Session:
        logger.error("neris_pack_import_no_db pack_id=%s correlation_id=%s", pack_id, correlation_id)
        return {"error": "no_db", "pack_id": pack_id}

    bucket = os.environ.get("S3_BUCKET_DOCS", "")
    zip_url = f"https://github.com/{repo}/archive/{ref}.zip"

    try:
        req = urllib.request.Request(zip_url, headers={"User-Agent": "FusionEMS-NERIS/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_bytes = resp.read()
    except Exception as exc:
        logger.error("neris_pack_import_download_failed pack_id=%s error=%s correlation_id=%s", pack_id, exc, correlation_id)
        _update_pack_status(pack_id, tenant_id, "import_failed", correlation_id)
        return {"error": str(exc), "pack_id": pack_id}

    pack_sha256 = hashlib.sha256(zip_bytes).hexdigest()
    file_records = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            parts = name.split("/", 1)
            rel_path = parts[1] if len(parts) > 1 else name
            ext = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
            if ext not in ("yaml", "yml", "csv", "json", "md"):
                continue

            content = zf.read(name)
            file_sha = hashlib.sha256(content).hexdigest()
            s3_key = f"{PACK_S3_PREFIX}/{pack_id}/raw/{rel_path}"
            if bucket:
                ct = "application/json" if ext == "json" else "text/plain"
                put_bytes(bucket=bucket, key=s3_key, content=content, content_type=ct)
            file_records.append({"path": rel_path, "file_type": ext, "s3_key_raw": s3_key, "sha256": file_sha})

    db = _Session()
    try:
        tenant_uuid = uuid.UUID(tenant_id) if tenant_id else None
        actor_uuid = uuid.UUID(actor_user_id) if actor_user_id else None

        for fr in file_records:
            file_id = uuid.uuid4()
            db.execute(text("""
                INSERT INTO neris_pack_files (id, tenant_id, version, data, created_at, updated_at)
                VALUES (:id, :tid, 1, :data, now(), now())
            """), {
                "id": str(file_id),
                "tid": str(tenant_uuid) if tenant_uuid else None,
                "data": json.dumps({
                    "pack_id": pack_id,
                    "path": fr["path"],
                    "file_type": fr["file_type"],
                    "s3_key_raw": fr["s3_key_raw"],
                    "sha256": fr["sha256"],
                }),
            })

        db.execute(text("""
            UPDATE neris_packs
            SET data = jsonb_set(jsonb_set(jsonb_set(data, '{status}', '"staged"'), '{sha256}', :sha256), '{file_count}', :count),
                version = version + 1,
                updated_at = now()
            WHERE id = :pack_id
        """), {
            "sha256": json.dumps(pack_sha256),
            "count": json.dumps(len(file_records)),
            "pack_id": pack_id,
        })
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("neris_pack_import_db_error pack_id=%s error=%s correlation_id=%s", pack_id, exc, correlation_id)
    finally:
        db.close()

    compile_queue = os.environ.get("NERIS_PACK_COMPILE_QUEUE_URL", "")
    if compile_queue:
        try:
            boto3.client("sqs").send_message(
                QueueUrl=compile_queue,
                MessageGroupId=pack_id,
                MessageDeduplicationId=f"compile-{pack_id}",
                MessageBody=json.dumps({"job_type": "neris.pack.compile_rules", "pack_id": pack_id, "tenant_id": tenant_id, "actor_user_id": actor_user_id}),
            )
        except Exception as exc:
            logger.error("neris_pack_compile_enqueue_failed pack_id=%s error=%s correlation_id=%s", pack_id, exc, correlation_id)

    logger.info("neris_pack_import_done pack_id=%s files=%d sha256=%s correlation_id=%s", pack_id, len(file_records), pack_sha256, correlation_id)
    return {"pack_id": pack_id, "files": len(file_records), "sha256": pack_sha256}


def process_pack_compile(body: dict, correlation_id: str) -> dict:
    pack_id = body.get("pack_id", "")
    tenant_id = body.get("tenant_id", "")
    actor_user_id = body.get("actor_user_id", "")

    logger.info("neris_pack_compile_start pack_id=%s correlation_id=%s", pack_id, correlation_id)

    if not _Session:
        return {"error": "no_db", "pack_id": pack_id}

    db = _Session()
    try:
        from core_app.services.event_publisher import get_event_publisher
        from core_app.neris.pack_compiler import NERISPackCompiler
        import asyncio

        publisher = get_event_publisher()
        tid = uuid.UUID(tenant_id) if tenant_id else uuid.uuid4()
        aid = uuid.UUID(actor_user_id) if actor_user_id else None
        compiler = NERISPackCompiler(db, publisher, tid, aid)
        result = asyncio.run(compiler.compile_pack(uuid.UUID(pack_id), correlation_id=correlation_id))
        logger.info("neris_pack_compile_done pack_id=%s result=%s correlation_id=%s", pack_id, result, correlation_id)
        return result
    except Exception as exc:
        logger.exception("neris_pack_compile_error pack_id=%s error=%s correlation_id=%s", pack_id, exc, correlation_id)
        return {"error": str(exc), "pack_id": pack_id}
    finally:
        db.close()


def _update_pack_status(pack_id: str, tenant_id: str, status: str, correlation_id: str) -> None:
    if not _Session:
        return
    db = _Session()
    try:
        db.execute(text("""
            UPDATE neris_packs SET data = jsonb_set(data, '{status}', :status), updated_at = now()
            WHERE id = :pack_id
        """), {"status": json.dumps(status), "pack_id": pack_id})
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
