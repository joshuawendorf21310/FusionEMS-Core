from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def lambda_handler(event: dict, context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_fax_match(body)
        except Exception as exc:
            logger.exception(
                "fax_match_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_fax_match(message: dict) -> None:
    fax_id: str = message.get("fax_id", "")
    tenant_id: str | None = message.get("tenant_id")
    s3_key: str = message.get("s3_key", "")
    ocr_text: str = message.get("ocr_text", "")
    fax_date: str = message.get("fax_date", "")

    logger.info(
        "fax_match_start fax_id=%s tenant_id=%s s3_key=%s",
        fax_id, tenant_id, s3_key,
    )

    if not fax_id or not tenant_id:
        logger.warning("fax_match_missing_fields fax_id=%s tenant_id=%s", fax_id, tenant_id)
        return

    database_url = os.environ.get("DATABASE_URL", "")
    bucket = os.environ.get("S3_BUCKET_DOCS", "")

    qr_payload: dict | None = None
    if s3_key and bucket:
        qr_payload = _try_decode_qr_from_pdf(bucket=bucket, s3_key=s3_key)

    from core_app.fax.claim_matcher import ClaimMatcher

    if qr_payload:
        logger.info("fax_match_qr_decoded fax_id=%s payload_claim_id=%s", fax_id, qr_payload.get("claim_id"))
        match_result = _match_by_qr(
            fax_id=fax_id,
            tenant_id=tenant_id,
            qr_payload=qr_payload,
            database_url=database_url,
        )
        if match_result:
            _persist_status(
                fax_id=fax_id,
                status="auto_matched",
                matched_claim_id=match_result["claim_id"],
                suggested_matches=None,
                database_url=database_url,
            )
            logger.info("fax_match_auto_matched_qr fax_id=%s claim_id=%s", fax_id, match_result["claim_id"])
            return

    if ocr_text:
        matches = _match_probabilistic(
            fax_id=fax_id,
            tenant_id=tenant_id,
            ocr_text=ocr_text,
            fax_date=fax_date,
            database_url=database_url,
        )
        if matches:
            best = matches[0]
            if best["score"] >= 80:
                _attach_claim(
                    fax_id=fax_id,
                    tenant_id=tenant_id,
                    claim_id=best["claim_id"],
                    attachment_type="auto_probabilistic",
                    database_url=database_url,
                )
                _persist_status(
                    fax_id=fax_id,
                    status="auto_matched",
                    matched_claim_id=best["claim_id"],
                    suggested_matches=None,
                    database_url=database_url,
                )
                logger.info(
                    "fax_match_auto_matched_prob fax_id=%s claim_id=%s score=%s",
                    fax_id, best["claim_id"], best["score"],
                )
                return

            _persist_status(
                fax_id=fax_id,
                status="suggested",
                matched_claim_id=None,
                suggested_matches=matches[:5],
                database_url=database_url,
            )
            logger.info("fax_match_suggested fax_id=%s top_score=%s", fax_id, best["score"])
            return

    _persist_status(
        fax_id=fax_id,
        status="unmatched",
        matched_claim_id=None,
        suggested_matches=None,
        database_url=database_url,
    )
    logger.info("fax_match_unmatched fax_id=%s", fax_id)


def _try_decode_qr_from_pdf(*, bucket: str, s3_key: str) -> dict | None:
    try:
        import boto3
        s3 = boto3.client("s3")
        resp = s3.get_object(Bucket=bucket, Key=s3_key)
        pdf_bytes: bytes = resp["Body"].read()
    except Exception as exc:
        logger.warning("fax_match_s3_download_failed s3_key=%s error=%s", s3_key, exc)
        return None

    first_page_bytes: bytes = pdf_bytes
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            first_page_bytes = pix.tobytes("png")
        doc.close()
    except Exception as exc:
        logger.debug("fax_match_fitz_unavailable error=%s — using raw pdf bytes", exc)

    try:
        import io as _io
        from core_app.fax.claim_matcher import ClaimMatcher

        class _FakeMatcher(ClaimMatcher):
            def __init__(self):
                pass

        return _FakeMatcher().decode_qr_payload(first_page_bytes)
    except Exception as exc:
        logger.debug("fax_match_qr_decode_failed error=%s", exc)
        return None


def _match_by_qr(
    *,
    fax_id: str,
    tenant_id: str,
    qr_payload: dict,
    database_url: str,
) -> dict | None:
    if not database_url:
        return None
    try:
        import psycopg
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher
            matcher = ClaimMatcher(db, tenant_id)
            result = matcher.match_claim_by_qr(qr_payload)
            if result:
                import uuid
                claim_id = str(result.get("id", ""))
                matcher.attach_to_claim(fax_id, claim_id, "qr_match", actor="auto_qr")
                return {"claim_id": claim_id}
            return None
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error("fax_match_by_qr_failed fax_id=%s error=%s", fax_id, exc)
        return None


def _match_probabilistic(
    *,
    fax_id: str,
    tenant_id: str,
    ocr_text: str,
    fax_date: str,
    database_url: str,
) -> list[dict]:
    if not database_url:
        return []
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher
            matcher = ClaimMatcher(db, tenant_id)
            return matcher.match_claim_probabilistic(ocr_text, fax_date=fax_date)
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error("fax_match_probabilistic_failed fax_id=%s error=%s", fax_id, exc)
        return []


def _attach_claim(
    *,
    fax_id: str,
    tenant_id: str,
    claim_id: str,
    attachment_type: str,
    database_url: str,
) -> None:
    if not database_url:
        return
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher
            matcher = ClaimMatcher(db, tenant_id)
            matcher.attach_to_claim(fax_id, claim_id, attachment_type, actor="auto_worker")
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error("fax_match_attach_failed fax_id=%s claim_id=%s error=%s", fax_id, claim_id, exc)


def _persist_status(
    *,
    fax_id: str,
    status: str,
    matched_claim_id: str | None,
    suggested_matches: list[dict] | None,
    database_url: str,
) -> None:
    if not database_url:
        logger.error("fax_match_persist_skipped DATABASE_URL not set")
        return

    now = datetime.now(timezone.utc).isoformat()
    suggested_json = json.dumps(suggested_matches or [], default=str)

    try:
        import psycopg
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE fax_documents
                    SET status = %s,
                        matched_claim_id = COALESCE(%s, matched_claim_id),
                        suggested_matches = %s::jsonb,
                        updated_at = %s
                    WHERE fax_id = %s
                    """,
                    (status, matched_claim_id, suggested_json, now, fax_id),
                )
            conn.commit()
    except Exception as exc:
        logger.error("fax_match_persist_failed fax_id=%s error=%s", fax_id, exc)
