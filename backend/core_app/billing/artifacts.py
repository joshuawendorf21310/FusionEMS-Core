from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from core_app.documents.s3_storage import default_exports_bucket, presign_get, put_bytes


def store_edi_artifact(*, db: Session, tenant_id: str, artifact_type: str, file_name: str, content: bytes, content_type: str) -> dict[str, Any]:
    bucket = default_exports_bucket()
    if not bucket:
        raise ValueError("exports_bucket_not_configured")
    key = f"tenants/{tenant_id}/edi/{artifact_type}/{file_name}"
    ref = put_bytes(bucket=bucket, key=key, content=content, content_type=content_type)
    return {"bucket": ref.bucket, "key": ref.key, "download_url": presign_get(bucket=ref.bucket, key=ref.key)}
