from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository


class ClaimMatcher:
    def __init__(self, db: Session, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def decode_qr_payload(self, image_bytes: bytes) -> dict | None:
        import io as _io
        decoded_text: str | None = None

        try:
            import zxingcpp
            import numpy as np
            from PIL import Image as PILImage
            img = PILImage.open(_io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
            results = zxingcpp.read_barcodes(arr)
            if results:
                decoded_text = results[0].text
        except Exception:
            pass

        if decoded_text is None:
            try:
                from pyzbar.pyzbar import decode as pyzbar_decode
                import PIL.Image
                img = PIL.Image.open(_io.BytesIO(image_bytes))
                results = pyzbar_decode(img)
                if results:
                    decoded_text = results[0].data.decode("utf-8", errors="replace")
            except Exception:
                pass

        if decoded_text is None:
            return None

        try:
            return json.loads(decoded_text)
        except Exception:
            return None

    def match_claim_by_qr(self, qr_payload: dict) -> dict | None:
        claim_id_raw = qr_payload.get("claim_id")
        if not claim_id_raw:
            return None
        try:
            import uuid
            cid = uuid.UUID(str(claim_id_raw))
        except Exception:
            return None
        repo = DominationRepository(self.db, table="billing_cases")
        try:
            import uuid
            return repo.get(tenant_id=uuid.UUID(self.tenant_id), record_id=cid)
        except Exception:
            return None

    def match_claim_probabilistic(self, ocr_text: str, fax_date: str = "") -> list[dict]:
        patient_names: list[str] = []
        for line in ocr_text.splitlines():
            m = re.match(r"(?:Patient|Name)\s*[:\-]\s*(.+)", line, re.IGNORECASE)
            if m:
                patient_names.append(m.group(1).strip())

        dob_patterns: list[str] = re.findall(
            r"\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b", ocr_text
        )

        member_ids: list[str] = []
        for pat in [r"Member\s*ID\s*[:\-]\s*(\S+)", r"Policy\s*[:\-]\s*(\S+)", r"ID#\s*(\S+)"]:
            member_ids.extend(re.findall(pat, ocr_text, re.IGNORECASE))

        claim_numbers: list[str] = re.findall(r"\b(\d{6,12})\b", ocr_text)

        import uuid
        try:
            tenant_uuid = uuid.UUID(self.tenant_id)
        except Exception:
            return []

        pg_trgm_available = self._check_pg_trgm()

        cases: list[dict] = []
        for patient_name in patient_names[:3]:
            if pg_trgm_available:
                try:
                    rows = self.db.execute(
                        text(
                            "SELECT id, data, tenant_id, version, created_at "
                            "FROM billing_cases "
                            "WHERE tenant_id = :tid AND deleted_at IS NULL "
                            "AND similarity(data->>'patient_last_name' || ' ' || data->>'patient_first_name', :name) > 0.25 "
                            "ORDER BY similarity(data->>'patient_last_name' || ' ' || data->>'patient_first_name', :name) DESC "
                            "LIMIT 20"
                        ),
                        {"tid": str(tenant_uuid), "name": patient_name},
                    ).mappings().all()
                    cases.extend([dict(r) for r in rows])
                except Exception:
                    rows = self.db.execute(
                        text(
                            "SELECT id, data, tenant_id, version, created_at "
                            "FROM billing_cases "
                            "WHERE tenant_id = :tid AND deleted_at IS NULL "
                            "AND (data->>'patient_last_name' ILIKE :name OR data->>'patient_first_name' ILIKE :name) "
                            "LIMIT 20"
                        ),
                        {"tid": str(tenant_uuid), "name": f"%{patient_name}%"},
                    ).mappings().all()
                    cases.extend([dict(r) for r in rows])
            else:
                for name_fragment in patient_name.split()[:2]:
                    try:
                        rows = self.db.execute(
                            text(
                                "SELECT id, data, tenant_id, version, created_at "
                                "FROM billing_cases "
                                "WHERE tenant_id = :tid AND deleted_at IS NULL "
                                "AND (data->>'patient_last_name' ILIKE :frag OR data->>'patient_first_name' ILIKE :frag) "
                                "LIMIT 20"
                            ),
                            {"tid": str(tenant_uuid), "frag": f"%{name_fragment}%"},
                        ).mappings().all()
                        cases.extend([dict(r) for r in rows])
                    except Exception:
                        pass

        if claim_numbers:
            for cn in claim_numbers[:3]:
                try:
                    rows = self.db.execute(
                        text(
                            "SELECT id, data, tenant_id, version, created_at "
                            "FROM billing_cases "
                            "WHERE tenant_id = :tid AND deleted_at IS NULL "
                            "AND data->>'claim_id' ILIKE :cn "
                            "LIMIT 5"
                        ),
                        {"tid": str(tenant_uuid), "cn": f"%{cn}%"},
                    ).mappings().all()
                    cases.extend([dict(r) for r in rows])
                except Exception:
                    pass

        seen_ids: set[str] = set()
        unique_cases: list[dict] = []
        for c in cases:
            cid = str(c.get("id", ""))
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique_cases.append(c)

        results: list[dict] = []
        for case in unique_cases:
            score = 0
            match_fields: list[str] = []
            cdata = case.get("data") or {}
            if isinstance(cdata, str):
                try:
                    cdata = json.loads(cdata)
                except Exception:
                    cdata = {}

            case_full_name = (
                (cdata.get("patient_last_name", "") + " " + cdata.get("patient_first_name", "")).strip().lower()
            )
            for pn in patient_names:
                if case_full_name and pn.lower() in case_full_name or case_full_name in pn.lower():
                    score += 40
                    match_fields.append("patient_name")
                    break

            case_dob = cdata.get("patient_dob", "")
            for dob in dob_patterns:
                dob_norm = dob.replace("/", "-")
                if case_dob and (dob_norm in case_dob or case_dob in dob_norm):
                    score += 30
                    match_fields.append("dob")
                    break

            case_member_id = cdata.get("member_id", "")
            for mid in member_ids:
                if case_member_id and mid.lower() == case_member_id.lower():
                    score += 20
                    match_fields.append("member_id")
                    break

            if fax_date and cdata.get("dos"):
                try:
                    fax_dt = datetime.fromisoformat(fax_date.replace("Z", "+00:00"))
                    dos_dt = datetime.fromisoformat(cdata["dos"].replace("Z", "+00:00"))
                    if abs((fax_dt - dos_dt).days) <= 30:
                        score += 10
                        match_fields.append("date_proximity")
                except Exception:
                    pass

            if score >= 40:
                results.append({
                    "claim_id": str(case.get("id", "")),
                    "claim_data": cdata,
                    "score": score,
                    "confidence": round(score / 100, 2),
                    "match_fields": match_fields,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _check_pg_trgm(self) -> bool:
        try:
            self.db.execute(text("SELECT similarity('test', 'test')"))
            return True
        except Exception:
            return False

    def attach_to_claim(
        self,
        fax_id: str,
        claim_id: str,
        attachment_type: str,
        actor: str = "auto",
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.db.execute(
                text(
                    "INSERT INTO claim_documents "
                    "(fax_id, claim_id, attachment_type, attached_by, attached_at, tenant_id) "
                    "VALUES (:fax_id, :claim_id, :attachment_type, :actor, :now, :tid) "
                    "ON CONFLICT (fax_id, claim_id) DO UPDATE SET "
                    "attachment_type = EXCLUDED.attachment_type, attached_at = EXCLUDED.attached_at"
                ),
                {
                    "fax_id": fax_id,
                    "claim_id": claim_id,
                    "attachment_type": attachment_type,
                    "actor": actor,
                    "now": now,
                    "tid": self.tenant_id,
                },
            )
        except Exception:
            pass

        self.db.execute(
            text(
                "UPDATE fax_documents "
                "SET status = 'attached', matched_claim_id = :claim_id, updated_at = :now "
                "WHERE fax_id = :fax_id"
            ),
            {"claim_id": claim_id, "now": now, "fax_id": fax_id},
        )

        try:
            self.db.execute(
                text(
                    "INSERT INTO document_audit_events "
                    "(entity_type, entity_id, action, actor, tenant_id, occurred_at, meta) "
                    "VALUES ('fax_document', :fax_id, 'attached_to_claim', :actor, :tid, :now, :meta::jsonb)"
                ),
                {
                    "fax_id": fax_id,
                    "actor": actor,
                    "tid": self.tenant_id,
                    "now": now,
                    "meta": json.dumps({"claim_id": claim_id, "attachment_type": attachment_type}),
                },
            )
        except Exception:
            pass

        self.db.commit()
        return {
            "fax_id": fax_id,
            "claim_id": claim_id,
            "attachment_type": attachment_type,
            "attached_by": actor,
            "attached_at": now,
            "status": "attached",
        }
