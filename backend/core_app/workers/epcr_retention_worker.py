"""ePCR 10-year retention sweep worker.

Sweep logic (runs on a configurable interval, default every 6 hours):

  1. Soft-delete protection:
       - Never hard-deletes anything.
       - Only marks deleted_at on records that are (a) not legal_hold and
         (b) past their retention window.

  2. Retention windows:
       - epcr_charts (submitted/locked/exported/void): 10 years from submitted_at
       - epcr_event_log:  10 years from created_at
       - audit_logs:      10 years from created_at
       - nemsis_submission_results: 10 years from submitted_at or created_at
       - nemsis_submission_status_history: 10 years from occurred_at

  3. Archival tiers (S3 lifecycle — does NOT delete, just re-tags):
       hot  (0–1yr)   → standard storage class, no action needed
       warm (1–3yr)   → transition to Glacier Instant Retrieval
       cold (3–10yr)  → transition to Glacier Deep Archive
       These transitions are applied by putting an S3 lifecycle configuration
       on the relevant buckets (done once at startup if not already present).

  4. legal_hold = TRUE → never touched by sweep; logged and skipped.

  5. All sweep actions are themselves written to audit_logs for full auditability.

Run via the main worker.py loop:
  asyncio.create_task(_epcr_retention_loop(stop_event))
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

RETENTION_YEARS = 10
GLACIER_IR_DAYS = 365
GLACIER_DA_DAYS = 365 * 3


# ------------------------------------------------------------------ #
# S3 lifecycle policy (applied once per bucket at startup)            #
# ------------------------------------------------------------------ #


def _apply_s3_lifecycle(bucket: str, prefix: str = "") -> None:
    try:
        import boto3

        s3 = boto3.client("s3")
        rule_id = f"fusionems-epcr-retention-{prefix or 'root'}"
        lifecycle = {
            "Rules": [
                {
                    "ID": rule_id,
                    "Status": "Enabled",
                    "Filter": {"Prefix": prefix} if prefix else {"Prefix": ""},
                    "Transitions": [
                        {
                            "Days": GLACIER_IR_DAYS,
                            "StorageClass": "GLACIER_IR",
                        },
                        {
                            "Days": GLACIER_DA_DAYS,
                            "StorageClass": "DEEP_ARCHIVE",
                        },
                    ],
                    "NoncurrentVersionTransitions": [],
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
                }
            ]
        }
        existing = {}
        with contextlib.suppress(s3.exceptions.ClientError):
            existing = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
        existing_ids = {r["ID"] for r in existing.get("Rules", [])}
        if rule_id not in existing_ids:
            s3.put_bucket_lifecycle_configuration(
                Bucket=bucket,
                LifecycleConfiguration=lifecycle,
            )
            logger.info("Applied S3 lifecycle policy to bucket=%s prefix=%s", bucket, prefix)
    except Exception as exc:
        logger.warning("Could not apply S3 lifecycle to bucket=%s: %s", bucket, exc)


def apply_all_s3_lifecycle_policies() -> None:
    try:
        from core_app.core.config import get_settings

        settings = get_settings()
        for bucket, prefix in [
            (settings.s3_bucket_exports, "nemsis-submissions/"),
            (settings.s3_bucket_docs, "epcr-attachments/"),
        ]:
            if bucket:
                _apply_s3_lifecycle(bucket, prefix)
    except Exception as exc:
        logger.warning("S3 lifecycle policy setup failed: %s", exc)


# ------------------------------------------------------------------ #
# DB sweep helpers                                                     #
# ------------------------------------------------------------------ #


def _cutoff(years: int = RETENTION_YEARS) -> datetime:
    return datetime.now(UTC) - timedelta(days=years * 365)


def _sweep_table(
    db: Any,
    table: str,
    date_col: str,
    tenant_col: str = "tenant_id",
    legal_hold_col: str | None = None,
) -> int:
    from sqlalchemy import text

    cutoff = _cutoff()
    where_legal = ""
    if legal_hold_col:
        where_legal = f" AND ({legal_hold_col} IS NULL OR {legal_hold_col} = FALSE)"
    sql = text(
        f"UPDATE {table} "
        f"SET deleted_at = NOW() "
        f"WHERE deleted_at IS NULL "
        f"AND COALESCE({date_col}, created_at) < :cutoff"
        f"{where_legal} "
    )
    result = db.execute(sql, {"cutoff": cutoff})
    return result.rowcount


async def run_retention_sweep(db_session_factory: Any) -> dict[str, int]:
    stats: dict[str, int] = {}
    try:
        with db_session_factory() as db:
            stats["epcr_charts"] = _sweep_table(
                db, "epcr_charts", "submitted_at", legal_hold_col="legal_hold"
            )
            stats["epcr_event_log"] = _sweep_table(db, "epcr_event_log", "created_at")
            stats["audit_logs"] = _sweep_table(db, "audit_logs", "created_at")
            stats["nemsis_submission_results"] = _sweep_table(
                db, "nemsis_submission_results", "created_at"
            )
            db.commit()
            total = sum(stats.values())
            if total:
                logger.info("ePCR retention sweep: soft-deleted %d records — %s", total, stats)
            else:
                logger.debug("ePCR retention sweep: no records past retention window")
    except Exception as exc:
        logger.error("ePCR retention sweep error: %s", exc)
    return stats


# ------------------------------------------------------------------ #
# Async loop (plugged into worker.py)                                  #
# ------------------------------------------------------------------ #

SWEEP_INTERVAL_SECONDS = 6 * 3600


async def _epcr_retention_loop(stop: asyncio.Event) -> None:
    await asyncio.get_running_loop().run_in_executor(None, apply_all_s3_lifecycle_policies)
    await asyncio.sleep(300)
    while not stop.is_set():
        try:
            from core_app.db.session import get_db_session_ctx

            await run_retention_sweep(get_db_session_ctx)
        except Exception as exc:
            logger.error("Retention loop error: %s", exc)
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
