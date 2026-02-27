from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STATEMENTS_TABLE    = os.environ.get("STATEMENTS_TABLE") or ""
FAX_DOCS_TABLE      = "fax_documents"


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_fax_classify(body)
        except Exception as exc:
            logger.exception(
                "fax_classify_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_fax_classify(message: dict[str, Any]) -> None:
    fax_id: str = message.get("fax_id", "")
    tenant_id: str | None = message.get("tenant_id")
    s3_key: str = message.get("s3_key", "")
    sha256: str | None = message.get("sha256")
    case_id: str | None = message.get("case_id")

    logger.info(
        "fax_classify_start fax_id=%s tenant_id=%s s3_key=%s",
        fax_id, tenant_id, s3_key,
    )

    if not fax_id or not s3_key:
        logger.warning("fax_classify_missing_fields fax_id=%s s3_key=%s", fax_id, s3_key)
        return

    doc_type = _classify_document(s3_key)
    extracted_text = _extract_text(s3_key)
    refined_case_id = case_id or _match_case_from_text(extracted_text, tenant_id)
    status = "classified" if doc_type else "unclassified"

    _persist_results(
        fax_id=fax_id,
        doc_type=doc_type,
        case_id=refined_case_id,
        status=status,
        extracted_text=extracted_text,
        s3_key=s3_key,
        tenant_id=tenant_id,
    )

    logger.info(
        "fax_classify_done fax_id=%s doc_type=%s case_id=%s status=%s",
        fax_id, doc_type, refined_case_id, status,
    )


def _classify_document(s3_key: str) -> str | None:
    """
    Classify the fax document.
    Phase 1: rule-based heuristics on s3_key/metadata.
    Phase 2: LLM classification via AI service (future).
    Returns doc_type string or None.
    """
    key_lower = s3_key.lower()
    if "facesheet" in key_lower or "face_sheet" in key_lower:
        return "facesheet"
    if "eob" in key_lower or "explanation" in key_lower:
        return "eob"
    if "auth" in key_lower or "authorization" in key_lower:
        return "auth"
    if "insurance" in key_lower:
        return "insurance_card"
    return None


def _extract_text(s3_key: str) -> str:
    """
    Phase 1: return empty string (no OCR).
    Phase 2: use Textract or pdfplumber to extract text.
    """
    return ""


def _match_case_from_text(text: str, tenant_id: str | None) -> str | None:
    """
    Attempt to find a billing case ID mentioned in extracted text.
    Phase 1: regex for numeric case IDs.
    Phase 2: embedding similarity search.
    """
    import re
    matches = re.findall(r"\b\d{6,12}\b", text)
    if matches:
        return matches[0]
    return None


def _persist_results(
    *,
    fax_id: str,
    doc_type: str | None,
    case_id: str | None,
    status: str,
    extracted_text: str,
    s3_key: str,
    tenant_id: str | None,
) -> None:
    """
    Persist classification results back to Postgres fax_documents table.
    Uses a direct psycopg connection since this runs as an ECS worker task,
    not inside the FastAPI request context.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("fax_classify_persist_skipped DATABASE_URL not set")
        return

    try:
        import psycopg
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE fax_documents
                    SET doc_type = %s,
                        case_id  = %s,
                        status   = %s,
                        updated_at = %s
                    WHERE fax_id = %s
                    """,
                    (doc_type, case_id, status, datetime.now(timezone.utc).isoformat(), fax_id),
                )
            conn.commit()
    except Exception as exc:
        logger.error("fax_classify_persist_failed fax_id=%s error=%s", fax_id, exc)
