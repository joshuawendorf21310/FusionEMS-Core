from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3

from core_app.documents.s3_storage import put_bytes, presign_get


class EvidenceService:
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def store_attachment(
        self,
        chart_id: str,
        attachment_type: str,
        content: bytes,
        filename: str,
        content_type: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        attachment_id = str(uuid.uuid4())
        safe_filename = filename.replace(" ", "_")
        s3_key = f"epcr/{tenant_id}/{chart_id}/attachments/{attachment_id}_{safe_filename}"
        sha256 = hashlib.sha256(content).hexdigest()
        put_bytes(bucket=self.bucket, key=s3_key, content=content, content_type=content_type)
        return {
            "attachment_id": attachment_id,
            "s3_key": s3_key,
            "filename": filename,
            "attachment_type": attachment_type,
            "size_bytes": len(content),
            "sha256": sha256,
            "content_type": content_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_presigned_url(self, s3_key: str, expires_seconds: int = 300) -> str:
        return presign_get(bucket=self.bucket, key=s3_key, expires_seconds=expires_seconds)

    def add_provenance(
        self,
        chart: dict[str, Any],
        field_name: str,
        value: Any,
        source_type: str,
        source_attachment_id: str | None = None,
        confidence: float = 1.0,
        confirmed_by: str | None = None,
        bounding_box: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "field_name": field_name,
            "value": value,
            "source_type": source_type,
            "source_attachment_id": source_attachment_id or "",
            "confidence": confidence,
            "confirmed_by": confirmed_by or "",
            "confirmed_at": datetime.now(timezone.utc).isoformat() if confirmed_by else "",
            "bounding_box": bounding_box or {},
        }
        chart.setdefault("provenance", []).append(record)
        return record

    def get_field_provenance(self, chart: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
        return [p for p in chart.get("provenance", []) if p.get("field_name") == field_name]
