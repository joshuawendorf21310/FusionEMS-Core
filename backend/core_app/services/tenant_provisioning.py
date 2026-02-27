from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def provision_tenant(
    db: Session,
    tenant_name: str,
    contact_email: str,
    billing_tier: str = "starter",
    modules: list[str] | None = None,
    feature_flags: dict[str, Any] | None = None,
    cognito_user_pool_id: str = "",
    aws_region: str = "us-east-1",
) -> dict[str, Any]:
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    default_modules = modules or ["billing", "transportlink", "crewlink", "patient_portal"]
    default_flags = feature_flags or {
        "ai_narrative": True,
        "overlay_mode": True,
        "nemsis_export": False,
        "auto_appeals": True,
        "patient_portal": True,
        "fire_module": False,
        "cad_module": False,
    }
    tenant_id = uuid.uuid4()
    tenant_row: dict | None = None

    try:
        tenant_row = await svc.create(
            table="tenants",
            tenant_id=tenant_id,
            actor_user_id=None,
            data={
                "id": str(tenant_id),
                "name": tenant_name,
                "contact_email": contact_email,
                "billing_tier": billing_tier,
                "modules_enabled": default_modules,
                "feature_flags": default_flags,
                "status": "provisioning",
                "s3_prefix": f"tenants/{tenant_id}",
                "provisioned_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        if cognito_user_pool_id:
            try:
                import boto3
                cognito = boto3.client("cognito-idp", region_name=aws_region)
                try:
                    cognito.create_group(
                        UserPoolId=cognito_user_pool_id,
                        GroupName=f"tenant-{tenant_id}",
                        Description=f"Tenant group for {tenant_name}",
                    )
                    logger.info("Created Cognito group for tenant %s", tenant_id)
                except cognito.exceptions.GroupExistsException:
                    pass
            except Exception as e:
                logger.warning("Cognito group creation failed (non-blocking): %s", e)

        await svc.update(
            table="tenants",
            tenant_id=tenant_id,
            actor_user_id=None,
            record_id=uuid.UUID(str(tenant_row["id"])),
            expected_version=tenant_row.get("version", 1),
            patch={"status": "active"},
            correlation_id=None,
        )

    except Exception as exc:
        logger.error("Tenant provisioning failed for %s: %s", tenant_name, exc)
        if tenant_row is not None:
            try:
                await svc.update(
                    table="tenants",
                    tenant_id=tenant_id,
                    actor_user_id=None,
                    record_id=uuid.UUID(str(tenant_row["id"])),
                    expected_version=tenant_row.get("version", 1),
                    patch={"status": "failed", "error": str(exc)},
                    correlation_id=None,
                )
            except Exception:
                pass
        raise

    await publisher.publish(
        "tenant.provisioned",
        tenant_id=tenant_id,
        entity_id=tenant_id,
        payload={
            "tenant_id": str(tenant_id),
            "name": tenant_name,
            "billing_tier": billing_tier,
            "modules": default_modules,
        },
        entity_type="tenant",
    )

    logger.info("Tenant provisioned: %s (%s)", tenant_name, tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "name": tenant_name,
        "status": "active",
        "modules": default_modules,
        "feature_flags": default_flags,
        "s3_prefix": f"tenants/{tenant_id}",
    }
