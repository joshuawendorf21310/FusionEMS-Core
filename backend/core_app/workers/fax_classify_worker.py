from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

import boto3

from core_app.documents.classifier import classify_text

logger = logging.getLogger(__name__)

FAX_DOCS_TABLE = "fax_documents"
_TEXTRACT_POLL_INTERVAL_S = 5
_TEXTRACT_MAX_POLLS = 60


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

    bucket = os.environ.get("S3_BUCKET_DOCS", "")
    extracted_text = _extract_text(s3_key=s3_key, bucket=bucket)
    doc_type = _classify_document(s3_key=s3_key, extracted_text=extracted_text)
    refined_case_id = case_id or _match_case_from_text(extracted_text, tenant_id)
    status = "classified" if doc_type and doc_type != "other" else "unclassified"

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


def _extract_text(*, s3_key: str, bucket: str) -> str:
    if not bucket:
        logger.warning("fax_classify_no_bucket s3_key=%s — S3_BUCKET_DOCS not set", s3_key)
        return ""

    textract = boto3.client("textract")

    try:
        start_resp = textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": bucket, "Name": s3_key}}
        )
    except Exception as exc:
        logger.error("fax_classify_textract_start_failed s3_key=%s error=%s", s3_key, exc)
        return ""

    job_id: str = start_resp["JobId"]
    logger.info("fax_classify_textract_started s3_key=%s job_id=%s", s3_key, job_id)

    lines: list[str] = []
    next_token: str | None = None

    for attempt in range(_TEXTRACT_MAX_POLLS):
        time.sleep(_TEXTRACT_POLL_INTERVAL_S)
        try:
            kwargs: dict[str, Any] = {"JobId": job_id}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = textract.get_document_text_detection(**kwargs)
        except Exception as exc:
            logger.error(
                "fax_classify_textract_poll_failed job_id=%s attempt=%d error=%s",
                job_id, attempt, exc,
            )
            return ""

        job_status: str = resp.get("JobStatus", "")

        if job_status == "FAILED":
            logger.error(
                "fax_classify_textract_job_failed job_id=%s status_message=%s",
                job_id, resp.get("StatusMessage", ""),
            )
            return ""

        if job_status == "SUCCEEDED":
            for block in resp.get("Blocks", []):
                if block.get("BlockType") == "LINE":
                    lines.append(block.get("Text", ""))
            next_token = resp.get("NextToken")
            if not next_token:
                break
        else:
            logger.debug(
                "fax_classify_textract_in_progress job_id=%s attempt=%d", job_id, attempt
            )
    else:
        logger.error(
            "fax_classify_textract_timeout job_id=%s after %d polls",
            job_id, _TEXTRACT_MAX_POLLS,
        )
        return ""

    text = "\n".join(lines)
    logger.info(
        "fax_classify_textract_done job_id=%s characters=%d", job_id, len(text)
    )
    return text


def _classify_document(*, s3_key: str, extracted_text: str) -> str | None:
    if extracted_text.strip():
        return classify_text(extracted_text)

    key_lower = s3_key.lower()
    if "facesheet" in key_lower or "face_sheet" in key_lower:
        return "facesheet"
    if "eob" in key_lower or "explanation" in key_lower:
        return "eob"
    if "auth" in key_lower or "authorization" in key_lower:
        return "auth"
    if "insurance" in key_lower:
        return "insurance_card"
    if "pcs" in key_lower:
        return "pcs"
    if "denial" in key_lower:
        return "denial_letter"
    if "appeal" in key_lower:
        return "appeal_response"
    return None


def _match_case_from_text(text: str, tenant_id: str | None) -> str | None:
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
