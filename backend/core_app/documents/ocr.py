from __future__ import annotations

import datetime as dt
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session

from core_app.documents.classifier import classify_text
from core_app.repositories.domination_repository import DominationRepository


class TextractOcrService:
    """
    OCR via AWS Textract (primary).
    - start_document_text_detection on an S3 object
    - poll results via get_document_text_detection
    Stores extraction results into document_extractions.data:
      { job_id, status, text, blocks_summary }
    """

    def __init__(self, db: Session, tenant_id: str, bucket: str):
        self.db = db
        self.tenant_id = tenant_id
        self.bucket = bucket
        self.client = boto3.client("textract")

    def start_job(self, *, document_id: str, s3_key: str) -> dict[str, Any]:
        try:
            resp = self.client.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": self.bucket, "Name": s3_key}}
            )
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"textract_start_failed:{str(e)[:200]}") from e

        job_id = resp["JobId"]
        repo = DominationRepository(self.db, table="document_extractions")
        rec = repo.create(
            tenant_id=self.tenant_id,
            actor_user_id=None,
            data={
                "document_id": document_id,
                "job_id": job_id,
                "status": "running",
                "started_at": dt.datetime.utcnow().isoformat(),
            },
        )
        return rec

    def poll_job(self, *, extraction_id: str) -> dict[str, Any]:
        ex_repo = DominationRepository(self.db, table="document_extractions")
        extraction = ex_repo.get(tenant_id=self.tenant_id, record_id=extraction_id)
        if not extraction:
            raise ValueError("extraction_not_found")
        job_id = extraction["data"].get("job_id")
        if not job_id:
            raise ValueError("job_id_missing")

        try:
            resp = self.client.get_document_text_detection(JobId=job_id, MaxResults=1000)
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"textract_poll_failed:{str(e)[:200]}") from e

        status = resp.get("JobStatus", "UNKNOWN")
        blocks = resp.get("Blocks", []) or []

        lines = [b.get("Text", "") for b in blocks if b.get("BlockType") == "LINE" and b.get("Text")]
        text = "\n".join(lines).strip()
        doc_type = classify_text(text) if text else "other"

        patch = {
            "status": status.lower(),
            "completed_at": dt.datetime.utcnow().isoformat() if status in ("SUCCEEDED", "FAILED") else None,
            "text": text[:200000],
            "blocks_summary": {"lines": len(lines), "blocks": len(blocks)},
            "doc_type_guess": doc_type,
        }
        updated = ex_repo.update(
            tenant_id=self.tenant_id,
            record_id=extraction_id,
            actor_user_id=None,
            expected_version=extraction["version"],
            data_patch=patch,
        )

        if status == "SUCCEEDED":
            doc_id = extraction["data"].get("document_id")
            if doc_id:
                doc_repo = DominationRepository(self.db, table="documents")
                doc = doc_repo.get(tenant_id=self.tenant_id, record_id=doc_id)
                if doc:
                    doc_repo.update(
                        tenant_id=self.tenant_id,
                        record_id=doc_id,
                        actor_user_id=None,
                        expected_version=doc["version"],
                        data_patch={"doc_type": doc_type, "ocr_status": "succeeded"},
                    )
        return updated
