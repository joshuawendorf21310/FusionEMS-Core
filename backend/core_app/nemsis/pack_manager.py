from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from core_app.core.config import get_settings
from core_app.documents.s3_storage import put_bytes
from core_app.services.domination_service import DominationService

REQUIRED_ROLES_BY_PACK_TYPE: dict[str, list[str]] = {
    "national_xsd": ["national_xsd"],
    "national_schematron": ["national_schematron"],
    "wi_state_dataset": ["wi_state_dataset"],
    "wi_schematron": ["wi_schematron"],
    "cs_scenarios": ["cs_scenario"],
    "bundle": ["national_xsd", "national_schematron", "wi_state_dataset", "wi_schematron"],
}

CONTENT_TYPE_MAP: dict[str, str] = {
    "xsd": "application/xml",
    "sch": "application/xml",
    "xml": "application/xml",
    "zip": "application/zip",
    "json": "application/json",
}


class PackManager:
    def __init__(self, db, publisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self._svc = DominationService(db, publisher)
        self._tenant_id = tenant_id
        self._actor_user_id = actor_user_id

    async def create_pack(
        self,
        pack_name: str,
        description: str,
        nemsis_version: str,
        state_code: str,
        pack_type: str,
        notes: str = "",
    ) -> dict[str, Any]:
        return await self._svc.create(
            table="nemsis_resource_packs",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            data={
                "pack_name": pack_name,
                "description": description,
                "nemsis_version": nemsis_version,
                "state_code": state_code.upper(),
                "pack_type": pack_type,
                "status": "staged",
                "file_count": 0,
                "total_size_bytes": 0,
                "sha256_manifest": {},
                "activated_at": None,
                "activated_by": None,
                "notes": notes,
            },
            correlation_id=None,
        )

    async def ingest_file(
        self,
        pack_id: str,
        filename: str,
        content: bytes,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")

        sha256 = hashlib.sha256(content).hexdigest()
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        file_type = ext if ext in CONTENT_TYPE_MAP else "bin"
        detected_role = self._detect_role(filename, content)
        content_type = CONTENT_TYPE_MAP.get(file_type, "application/octet-stream")
        s3_key = f"nemsis/packs/{pack_id}/{filename}"
        bucket = get_settings().s3_bucket_docs

        put_bytes(bucket=bucket, key=s3_key, content=content, content_type=content_type)

        file_rec = await self._svc.create(
            table="nemsis_pack_files",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            data={
                "pack_id": pack_id,
                "filename": filename,
                "file_type": file_type,
                "detected_role": detected_role,
                "size_bytes": len(content),
                "sha256": sha256,
                "s3_key": s3_key,
                "content_type": content_type,
            },
            correlation_id=correlation_id,
        )

        pack_data: dict[str, Any] = dict(pack.get("data", {}))
        manifest: dict[str, str] = dict(pack_data.get("sha256_manifest", {}))
        manifest[filename] = sha256
        current_size = int(pack_data.get("total_size_bytes", 0))
        current_count = int(pack_data.get("file_count", 0))

        await self._svc.update(
            table="nemsis_resource_packs",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            record_id=uuid.UUID(str(pack["id"])),
            expected_version=int(pack.get("version", 1)),
            patch={
                "file_count": current_count + 1,
                "total_size_bytes": current_size + len(content),
                "sha256_manifest": manifest,
            },
            correlation_id=correlation_id,
        )

        return file_rec

    async def activate_pack(
        self,
        pack_id: str,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")

        pack_data: dict[str, Any] = pack.get("data", {})
        state_code = pack_data.get("state_code")
        pack_type = pack_data.get("pack_type")

        all_packs = self.list_packs()
        for other in all_packs:
            other_data = other.get("data", {})
            if (
                str(other.get("id")) != pack_id
                and other_data.get("state_code") == state_code
                and other_data.get("pack_type") == pack_type
                and other_data.get("status") == "active"
            ):
                await self._svc.update(
                    table="nemsis_resource_packs",
                    tenant_id=self._tenant_id,
                    actor_user_id=self._actor_user_id,
                    record_id=uuid.UUID(str(other["id"])),
                    expected_version=int(other.get("version", 1)),
                    patch={"status": "archived"},
                    correlation_id=correlation_id,
                )

        return await self._svc.update(
            table="nemsis_resource_packs",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            record_id=uuid.UUID(pack_id),
            expected_version=int(pack.get("version", 1)),
            patch={
                "status": "active",
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "activated_by": str(actor_user_id),
            },
            correlation_id=correlation_id,
        )

    async def stage_pack(self, pack_id: str, correlation_id: str | None = None) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")
        return await self._svc.update(
            table="nemsis_resource_packs",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            record_id=uuid.UUID(pack_id),
            expected_version=int(pack.get("version", 1)),
            patch={"status": "staged"},
            correlation_id=correlation_id,
        )

    async def archive_pack(self, pack_id: str, correlation_id: str | None = None) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")
        return await self._svc.update(
            table="nemsis_resource_packs",
            tenant_id=self._tenant_id,
            actor_user_id=self._actor_user_id,
            record_id=uuid.UUID(pack_id),
            expected_version=int(pack.get("version", 1)),
            patch={"status": "archived"},
            correlation_id=correlation_id,
        )

    def get_active_pack(self, state_code: str, pack_type: str) -> dict[str, Any] | None:
        packs = self.list_packs()
        for pack in packs:
            d = pack.get("data", {})
            if (
                d.get("state_code") == state_code.upper()
                and d.get("pack_type") == pack_type
                and d.get("status") == "active"
            ):
                return pack
        return None

    def list_packs(self) -> list[dict[str, Any]]:
        return self._svc.repo("nemsis_resource_packs").list(tenant_id=self._tenant_id)

    def get_pack(self, pack_id: str) -> dict[str, Any] | None:
        return self._svc.repo("nemsis_resource_packs").get(
            tenant_id=self._tenant_id, record_id=uuid.UUID(pack_id)
        )

    def list_pack_files(self, pack_id: str) -> list[dict[str, Any]]:
        return self._svc.repo("nemsis_pack_files").list_raw_by_field(
            "pack_id", pack_id, limit=500
        )

    def get_pack_completeness(self, pack_id: str) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if pack is None:
            return {"complete": False, "present": [], "missing": [], "detail": {}, "error": "Pack not found"}

        pack_type = pack.get("data", {}).get("pack_type", "bundle")
        required_roles = REQUIRED_ROLES_BY_PACK_TYPE.get(pack_type, [])

        files = self.list_pack_files(pack_id)
        present_roles = {f.get("data", {}).get("detected_role") for f in files}

        present = [r for r in required_roles if r in present_roles]
        missing = [r for r in required_roles if r not in present_roles]

        detail: dict[str, Any] = {}
        for role in required_roles:
            matching = [f for f in files if f.get("data", {}).get("detected_role") == role]
            detail[role] = {
                "required": True,
                "present": role in present_roles,
                "files": [f.get("data", {}).get("filename") for f in matching],
            }

        return {
            "complete": not missing,
            "present": present,
            "missing": missing,
            "detail": detail,
        }

    def _detect_role(self, filename: str, content: bytes) -> str:
        preview = content[:500].decode(errors="ignore")
        preview200 = content[:200].decode(errors="ignore")
        fname_upper = filename.upper()

        if "EMSDataSet" in filename and filename.endswith(".xsd"):
            return "national_xsd"
        if "DEMDataSet" in filename and filename.endswith(".xsd"):
            return "national_dem_xsd"
        if filename.endswith(".sch") and ("WI" in filename or "Wisconsin" in preview):
            return "wi_schematron"
        if filename.endswith(".sch"):
            return "national_schematron"
        if "StateDataSet" in filename and "WI" in fname_upper:
            return "wi_state_dataset"
        if filename.endswith(".xml") and "EMSDataSet" in preview200:
            return "ems_export_sample"
        if filename.endswith(".zip"):
            return "bundle_zip"
        if filename.endswith(".json") and "scenario" in preview200:
            return "cs_scenario"
        return "unknown"
