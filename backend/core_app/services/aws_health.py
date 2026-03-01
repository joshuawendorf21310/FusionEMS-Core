from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core_app.core.config import get_settings

logger = logging.getLogger(__name__)


def _cw_client():
    s = get_settings()
    return boto3.client("cloudwatch", region_name=s.aws_region or "us-east-1")


def _acm_client():
    s = get_settings()
    return boto3.client("acm", region_name=s.aws_region or "us-east-1")


def _rds_client():
    s = get_settings()
    return boto3.client("rds", region_name=s.aws_region or "us-east-1")


def _ce_client():
    return boto3.client("ce", region_name="us-east-1")


def _sm_client():
    s = get_settings()
    return boto3.client("secretsmanager", region_name=s.aws_region or "us-east-1")


def _safe(fn, fallback=None):
    try:
        return fn()
    except (BotoCoreError, ClientError) as exc:
        logger.warning("aws_health_call_failed: %s", exc)
        return fallback


def get_cw_metric_avg(namespace: str, metric_name: str, dimensions: list[dict], minutes: int = 5) -> float | None:
    def _call():
        cw = _cw_client()
        end = datetime.now(UTC)
        start = end - timedelta(minutes=minutes)
        resp = cw.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start,
            EndTime=end,
            Period=minutes * 60,
            Statistics=["Average"],
        )
        points = resp.get("Datapoints", [])
        if not points:
            return None
        latest = max(points, key=lambda p: p["Timestamp"])
        return round(latest["Average"], 2)
    return _safe(_call)


def get_ssl_expiration(domains: list[str]) -> list[dict[str, Any]]:
    def _call():
        acm = _acm_client()
        paginator = acm.get_paginator("list_certificates")
        certs = []
        for page in paginator.paginate(CertificateStatuses=["ISSUED"]):
            certs.extend(page.get("CertificateSummaryList", []))
        results = []
        for domain in domains:
            match = next((c for c in certs if c.get("DomainName") == domain), None)
            if match:
                detail = acm.describe_certificate(CertificateArn=match["CertificateArn"])
                cert = detail["Certificate"]
                not_after = cert.get("NotAfter")
                if not_after:
                    days_left = (not_after - datetime.now(UTC)).days
                    results.append({"domain": domain, "expires_in_days": days_left, "status": "valid" if days_left > 30 else "expiring"})
                else:
                    results.append({"domain": domain, "expires_in_days": None, "status": "unknown"})
            else:
                results.append({"domain": domain, "expires_in_days": None, "status": "not_found"})
        return results
    return _safe(_call, fallback=[{"domain": d, "expires_in_days": None, "status": "unavailable"} for d in domains])


def get_rds_backup_status(db_instance_id: str) -> dict[str, Any]:
    def _call():
        rds = _rds_client()
        resp = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        inst = resp["DBInstances"][0]
        retention = inst.get("BackupRetentionPeriod", 0)
        latest = inst.get("LatestRestorableTime")
        return {
            "status": "healthy" if retention > 0 else "no_backup",
            "last_backup": latest.isoformat() if latest else None,
            "retention_days": retention,
        }
    return _safe(_call, fallback={"status": "unavailable", "last_backup": None, "retention_days": 0})


def get_cost_mtd() -> dict[str, Any]:
    def _call():
        ce = _ce_client()
        now = datetime.now(UTC)
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        results = resp.get("ResultsByTime", [])
        if results:
            amount = float(results[0]["Total"]["UnblendedCost"]["Amount"])
            return {"estimated_spend_usd": round(amount, 2)}
        return {"estimated_spend_usd": 0}
    return _safe(_call, fallback={"estimated_spend_usd": None})


def get_secret_metadata(secret_id: str) -> dict[str, Any] | None:
    def _call():
        sm = _sm_client()
        resp = sm.describe_secret(SecretId=secret_id)
        last_changed = resp.get("LastChangedDate")
        last_rotated = resp.get("LastRotatedDate")
        return {
            "last_changed": last_changed.isoformat() if last_changed else None,
            "last_rotated": last_rotated.isoformat() if last_rotated else None,
        }
    return _safe(_call)


def get_db_connections(db_instance_id: str) -> dict[str, Any]:
    val = get_cw_metric_avg(
        "AWS/RDS", "DatabaseConnections",
        [{"Name": "DBInstanceIdentifier", "Value": db_instance_id}],
    )
    return {"active_connections": val if val is not None else 0, "max_connections": 500, "pool_utilization_pct": round((val or 0) / 500 * 100, 1)}
