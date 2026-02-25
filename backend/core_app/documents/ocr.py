from __future__ import annotations

import datetime as dt
import os
import uuid
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository


class TextractOcrService:
    """OCR via AWS Textract (primary).
    Requires documents stored in S3; document record must contain bucket and s3_key.
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.repo_docs = DominationRepository(db, table="documents")
        self.repo_ext = DominationRepository(db, table="document_extractions")
        self.client = boto3.client("textract")

    def _now(self) -> str:
        return dt.datetime.now(tz=dt.timezone.utc).isoformat()

    def start_text_detection(self, document_id: uuid.UUID) -> dict[str, Any]:
        doc = self.repo_docs.get(self.tenant_id, document_id)
        if not doc:
            raise ValueError("document_not_found")
        d = doc["data"]
        bucket = d.get("bucket") or os.getenv("DOCS_BUCKET")
        s3_key = d.get("s3_key")
        if not bucket or not s3_key:
            raise ValueError("document_missing_s3_location")

        try:
            resp = self.client.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": bucket, "Name": s3_key}}
            )
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"textract_start_failed:{e}") from e

        job_id = resp["JobId"]
        extraction = self.repo_ext.create(
            self.tenant_id,
            data={
                "document_id": str(document_id),
                "provider": "textract",
                "job_id": job_id,
                "status": "running",
                "started_at": self._now(),
            },
        )
        return {"job_id": job_id, "extraction_id": str(extraction["id"])}

    def get_job(self, job_id: str, max_pages: int = 10) -> dict[str, Any]:
        # Pull results (limited) - caller can store full blocks elsewhere if desired.
        blocks: list[dict[str, Any]] = []
        next_token = None
        pages = 0
        status = "running"
        try:
            while pages < max_pages:
                kwargs = {"JobId": job_id}
                if next_token:
                    kwargs["NextToken"] = next_token
                res = self.client.get_document_text_detection(**kwargs)
                status = res.get("JobStatus","running").lower()
                blocks.extend(res.get("Blocks") or [])
                next_token = res.get("NextToken")
                pages += 1
                if not next_token:
                    break
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"textract_get_failed:{e}") from e
        return {"status": status, "blocks": blocks, "pages": pages}
