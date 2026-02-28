"""JCS (RFC 8785) canonical JSON serialisation + SHA-256.

Rules:
  - Object keys sorted lexicographically (Unicode code-point order)
  - No insignificant whitespace
  - UTF-8 encoded
  - Arrays preserved in original order
  - NaN / Infinity raise ValueError (not representable in JSON)
  - Numbers serialised without trailing zeros; integers without decimal point

Usage::

    from core_app.epcr.jcs_hash import jcs_canonicalize, jcs_sha256

    payload = {"z": 1, "a": 2, "nested": {"b": True}}
    canonical: bytes = jcs_canonicalize(payload)
    hexdigest: str   = jcs_sha256(payload)

The hash is deterministic: identical clinical content always yields the same
hex string regardless of insertion order or timestamp formatting, provided the
caller excludes volatile fields before passing the payload.

Hash payload contract for epcr_charts (exclude these fields):
  updated_at, completeness_score, completeness_issues, sync_status,
  _event_log, attachments (S3 keys are volatile)

Include:
  chart_id, tenant_id, chart_mode, schema_version (default "3.5"),
  patient, consent, dispatch, vitals, medications, procedures,
  assessments, disposition, narrative, acls, cct, hems,
  created_at, created_by, submitted_at
"""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any


_VOLATILE_TOP_LEVEL = frozenset({
    "updated_at",
    "completeness_score",
    "completeness_issues",
    "sync_status",
    "_event_log",
    "attachments",
    "last_modified_by",
    "chart_status",
})


def _jcs_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            raise ValueError(f"JCS does not permit NaN or Infinity, got: {value!r}")
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"JCS does not permit NaN or Infinity, got: {value!r}")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {k: _jcs_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_jcs_value(item) for item in value]
    raise TypeError(f"JCS: unsupported type {type(value)!r} for value {value!r}")


def jcs_canonicalize(obj: Any) -> bytes:
    """Return RFC 8785 canonical UTF-8 JSON bytes for *obj*."""
    normalised = _jcs_value(obj)
    return json.dumps(
        normalised,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def jcs_sha256(obj: Any) -> str:
    """Return lowercase hex SHA-256 of the JCS canonical form of *obj*."""
    return hashlib.sha256(jcs_canonicalize(obj)).hexdigest()


def build_chart_hash_payload(chart_data: dict[str, Any]) -> dict[str, Any]:
    """Return the subset of chart_data used for sha256_submitted.

    Strips volatile/UI-only fields so the hash is stable across repeated
    submits with identical clinical content.
    """
    return {k: v for k, v in chart_data.items() if k not in _VOLATILE_TOP_LEVEL}
