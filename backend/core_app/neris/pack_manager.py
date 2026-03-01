from __future__ import annotations  # noqa: E402

"""
NERIS Pack Manager.

Pulls the ulfsri/neris-framework repo zip from GitHub, stores raw files in S3,
records neris_packs + neris_pack_files rows via DominationService.
"""

import os  # noqa: E402
import uuid  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

from sqlalchemy.orm import Session  # noqa: E402

from core_app.services.domination_service import DominationService  # noqa: E402
from core_app.services.event_publisher import EventPublisher  # noqa: E402

GITHUB_ZIP_URL = "https://github.com/{repo}/archive/{ref}.zip"
PACK_S3_PREFIX = "neris/packs"


class NERISPackManager:
    def __init__(self, db: Session, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    async def import_from_github(
        self,
        repo: str,
        ref: str,
        name: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        pack = await self.svc.create(
            table="neris_packs",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "name": name,
                "source_type": "github",
                "source_uri": f"https://github.com/{repo}",
                "source_ref": ref,
                "status": "importing",
                "sha256": "",
                "compiled": False,
            },
            correlation_id=correlation_id,
        )
        pack_id = str(pack["id"])

        _enqueue_pack_import(pack_id=pack_id, repo=repo, ref=ref, name=name, tenant_id=str(self.tenant_id), actor_user_id=str(self.actor_user_id))
        return pack

    async def activate_pack(self, pack_id: uuid.UUID, correlation_id: str | None = None) -> dict[str, Any]:
        pack = self.svc.repo("neris_packs").get(tenant_id=self.tenant_id, record_id=pack_id)
        if not pack:
            raise ValueError("pack_not_found")
        pdata = pack.get("data") or {}
        if pdata.get("status") not in ("staged", "compiled"):
            raise ValueError("pack_not_ready_to_activate")

        all_packs = self.svc.repo("neris_packs").list(tenant_id=self.tenant_id, limit=100)
        for p in all_packs:
            pd = p.get("data") or {}
            if pd.get("status") == "active" and str(p["id"]) != str(pack_id):
                pd["status"] = "archived"
                await self.svc.update(
                    table="neris_packs",
                    tenant_id=self.tenant_id,
                    record_id=uuid.UUID(str(p["id"])),
                    actor_user_id=self.actor_user_id,
                    patch=pd,
                    expected_version=p.get("version", 1),
                    correlation_id=correlation_id,
                )

        pdata["status"] = "active"
        pdata["activated_at"] = datetime.now(UTC).isoformat()
        updated = await self.svc.update(
            table="neris_packs",
            tenant_id=self.tenant_id,
            record_id=pack_id,
            actor_user_id=self.actor_user_id,
            patch=pdata,
            expected_version=pack.get("version", 1),
            correlation_id=correlation_id,
        )
        return updated

    def get_active_pack(self) -> dict[str, Any] | None:
        packs = self.svc.repo("neris_packs").list(tenant_id=self.tenant_id, limit=100)
        for p in packs:
            if (p.get("data") or {}).get("status") == "active":
                return p
        return None

    def list_packs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.svc.repo("neris_packs").list(tenant_id=self.tenant_id, limit=limit)

    def get_pack(self, pack_id: uuid.UUID) -> dict[str, Any] | None:
        return self.svc.repo("neris_packs").get(tenant_id=self.tenant_id, record_id=pack_id)

    def get_compiled_rules(self, pack_id: uuid.UUID, entity_type: str) -> dict[str, Any] | None:
        rules = self.svc.repo("neris_compiled_rules").list(tenant_id=self.tenant_id, limit=20)
        for r in rules:
            rd = r.get("data") or {}
            if rd.get("pack_id") == str(pack_id) and rd.get("entity_type") == entity_type:
                return rd.get("rules_json")
        return None


def _enqueue_pack_import(*, pack_id: str, repo: str, ref: str, name: str, tenant_id: str, actor_user_id: str) -> None:
    import json  # noqa: E402

    import boto3  # noqa: E402
    queue_url = os.environ.get("NERIS_PACK_IMPORT_QUEUE_URL", "")
    if not queue_url:
        return
    import logging as _logging  # noqa: E402
    _log = _logging.getLogger(__name__)
    try:
        sqs = boto3.client("sqs")
        sqs.send_message(
            QueueUrl=queue_url,
            MessageGroupId=pack_id,
            MessageDeduplicationId=pack_id,
            MessageBody=json.dumps({
                "job_type": "neris.pack.import",
                "pack_id": pack_id,
                "repo": repo,
                "ref": ref,
                "name": name,
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
            }),
        )
    except Exception as exc:
        _log.error("neris_pack_import_enqueue_failed pack_id=%s error=%s", pack_id, exc)
