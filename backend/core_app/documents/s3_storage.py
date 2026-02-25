from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Optional

import boto3

from core_app.core.config import get_settings


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str


def put_bytes(*, bucket: str, key: str, content: bytes, content_type: str = "application/octet-stream") -> S3ObjectRef:
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    return S3ObjectRef(bucket=bucket, key=key)


def presign_get(*, bucket: str, key: str, expires_seconds: int = 300) -> str:
    s3 = boto3.client("s3")
    return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_seconds)


def default_exports_bucket() -> str:
    return get_settings().s3_bucket_exports


def default_docs_bucket() -> str:
    return get_settings().s3_bucket_docs
