from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.billing.x12_837p import build_837p_ambulance
from core_app.billing.x12_835 import parse_835 as _parse_835_base
from core_app.repositories.domination_repository import DominationRepository
from core_app.services.domination_service import DominationService

logger = logging.getLogger(__name__)

try:
    import pyx12  # noqa: F401
    import pyx12.x12context  # noqa: F401
    PYX12_AVAILABLE = True
except ImportError:
    PYX12_AVAILABLE = False

try:
    from linuxforhealth.x12.io import X12ModelReader  # noqa: F401
    LFH_AVAILABLE = True
except ImportError:
    LFH_AVAILABLE = False

_277_STATUS_MAP: dict[str, str] = {
    "A1": "Acknowledged",
    "A2": "Accepted",
    "A3": "Returned",
    "A4": "Not Found",
    "A6": "Rejected",
    "A7": "Acknowledged",
    "P1": "Pending",
    "R1": "Rejected",
    "R3": "Rejected - Invalid Provider",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class EDIService:
    def __init__(self, db: Session, publisher: Any, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.publisher = publisher
        self.tenant_id = tenant_id
        self.svc = DominationService(db, publisher)

    async def generate_837_batch(self, claim_ids: list[str], submitter_config: dict) -> dict:
        x12_segments: list[str] = []
        validated = True
        all_validation_errors: list[str] = []

        for claim_id_str in claim_ids:
            try:
                claim_uuid = uuid.UUID(claim_id_str)
            except Exception:
                all_validation_errors.append(f"invalid_claim_id: {claim_id_str}")
                continue

            case = DominationRepository(self.db, table="billing_cases").get(
                tenant_id=self.tenant_id, record_id=claim_uuid
            )
            if not case:
                all_validation_errors.append(f"claim_not_found: {claim_id_str}")
                continue

            cdata = case.get("data") or {}
            patient = cdata.get("patient") or {}
            claim = {
                "claim_id": cdata.get("claim_id", claim_id_str),
                "dos": cdata.get("dos", ""),
                "member_id": cdata.get("member_id", ""),
                "billing_name": cdata.get("billing_name", "FUSIONEMSQUANTUM"),
                "billing_address1": cdata.get("billing_address1", "UNKNOWN"),
                "billing_city": cdata.get("billing_city", "UNKNOWN"),
                "billing_state": cdata.get("billing_state", "WI"),
                "billing_zip": cdata.get("billing_zip", "00000"),
                "submitter_name": submitter_config.get("submitter_name", "FUSIONEMSQUANTUM"),
                "submitter_contact": submitter_config.get("submitter_contact", "BILLING"),
                "submitter_phone": submitter_config.get("submitter_phone", "0000000000"),
                "receiver_name": submitter_config.get("receiver_name", "OFFICEALLY"),
                "insurance_type": cdata.get("insurance_type", "CI"),
            }
            service_lines = cdata.get("service_lines") or []

            x12_text, _env = build_837p_ambulance(
                submitter_id=submitter_config.get("submitter_id", "FUSIONEMS"),
                receiver_id=submitter_config.get("receiver_id", "OFFICEALLY"),
                billing_npi=submitter_config.get("billing_npi", "0000000000"),
                billing_tax_id=submitter_config.get("billing_tax_id", "000000000"),
                patient=patient,
                claim=claim,
                service_lines=service_lines,
            )

            errs = self._validate_837_pyx12(x12_text)
            if errs:
                validated = False
                all_validation_errors.extend([f"{claim_id_str}: {e}" for e in errs])

            x12_segments.append(x12_text)

        bundle = "\n".join(x12_segments)
        sha256 = hashlib.sha256(bundle.encode("utf-8")).hexdigest()
        content_b64 = base64.b64encode(bundle.encode("utf-8")).decode("ascii")

        batch_record = await self.svc.create(
            table="edi_artifacts",
            tenant_id=self.tenant_id,
            actor_user_id=None,
            data={
                "entity_type": "submission_batch",
                "claim_ids": claim_ids,
                "file_type": "837P_BATCH",
                "content_b64": content_b64,
                "sha256": sha256,
                "status": "generated",
                "submitter_id": submitter_config.get("submitter_id", ""),
                "batch_date": _utcnow(),
                "claim_count": len(claim_ids),
                "validated": validated,
                "validation_errors": all_validation_errors,
            },
            correlation_id=None,
        )
        batch_id = str(batch_record["id"])

        await self.svc.create(
            table="edi_artifacts",
            tenant_id=self.tenant_id,
            actor_user_id=None,
            data={
                "entity_type": "edi_file",
                "batch_id": batch_id,
                "file_type": "837P",
                "content_b64": content_b64,
                "sha256": sha256,
                "status": "generated",
            },
            correlation_id=None,
        )

        return {
            "batch_id": batch_id,
            "claim_count": len(claim_ids),
            "sha256": sha256,
            "validated": validated,
            "validation_errors": all_validation_errors,
        }

    def _validate_837_pyx12(self, x12_text: str) -> list[str]:
        if not PYX12_AVAILABLE:
            logger.warning("pyx12 not installed — skipping 837P validation")
            return []
        errors: list[str] = []
        try:
            import io
            import pyx12.error_handler
            import pyx12.params
            import pyx12.x12file
            param = pyx12.params.params()
            errh = pyx12.error_handler.errh_null()
            src = pyx12.x12file.X12Reader(io.StringIO(x12_text))
            ctx = pyx12.x12context.X12ContextReader(param, errh, src)
            for seg, seg_data, trig_node, loop_node in ctx.iter_segments():
                if errh.err_count > 0:
                    errors.append(f"pyx12_error seg={seg}")
        except Exception as exc:
            errors.append(f"pyx12_exception: {exc}")
        return errors

    def parse_999(self, x12_text: str, batch_id: str) -> dict:
        isa_control: str = ""
        accepted = True
        rejected_count = 0
        error_segments: list[str] = []

        if LFH_AVAILABLE:
            try:
                reader = X12ModelReader(x12_text)
                for m in reader.models():
                    model_dict = m.dict() if hasattr(m, "dict") else {}
                    isa_control = str(model_dict.get("interchange_control_number", ""))
                    ak5_list = model_dict.get("ak5", [])
                    if isinstance(ak5_list, list):
                        for ak5 in ak5_list:
                            disp = ak5.get("functional_group_acknowledge_code", "")
                            if disp not in ("A", "E"):
                                accepted = False
                                rejected_count += 1
                    elif isinstance(ak5_list, dict):
                        disp = ak5_list.get("functional_group_acknowledge_code", "")
                        if disp not in ("A", "E"):
                            accepted = False
                            rejected_count += 1
            except Exception as exc:
                logger.warning("lfh_999_parse_failed error=%s — falling back to manual", exc)
                return self._parse_999_manual(x12_text, batch_id)
        else:
            return self._parse_999_manual(x12_text, batch_id)

        status = "accepted" if accepted else "rejected"
        self._update_batch_status(batch_id=batch_id, status=status)

        return {
            "batch_id": batch_id,
            "isa_control": isa_control,
            "accepted": accepted,
            "rejected_count": rejected_count,
            "error_segments": error_segments,
            "source": "linuxforhealth",
        }

    def _parse_999_manual(self, x12_text: str, batch_id: str) -> dict:
        segments = [s.strip() for s in x12_text.split("~") if s.strip()]
        isa_control = ""
        accepted = True
        rejected_count = 0
        error_segments: list[str] = []

        for seg in segments:
            parts = seg.split("*")
            tag = parts[0].strip()
            if tag == "ISA" and len(parts) > 13:
                isa_control = parts[13].strip()
            if tag == "AK5" and len(parts) > 1:
                code = parts[1].strip()
                if code not in ("A", "E"):
                    accepted = False
                    rejected_count += 1
                    error_segments.append(seg)
            if tag == "AK3" and len(parts) > 3:
                error_segments.append(seg)

        status = "accepted" if accepted else "rejected"
        self._update_batch_status(batch_id=batch_id, status=status)
        self._update_claim_status_history_from_999(batch_id=batch_id, accepted=accepted)

        return {
            "batch_id": batch_id,
            "isa_control": isa_control,
            "accepted": accepted,
            "rejected_count": rejected_count,
            "error_segments": error_segments,
            "source": "manual",
        }

    def _update_batch_status(self, *, batch_id: str, status: str) -> None:
        try:
            batch_uuid = uuid.UUID(batch_id)
        except Exception:
            return
        repo = DominationRepository(self.db, table="edi_artifacts")
        existing = repo.get(tenant_id=self.tenant_id, record_id=batch_uuid)
        if existing:
            repo.update(
                tenant_id=self.tenant_id,
                record_id=batch_uuid,
                expected_version=existing["version"],
                patch={"status": status, "acknowledged_at": _utcnow()},
            )
            self.db.commit()

    def _update_claim_status_history_from_999(self, *, batch_id: str, accepted: bool) -> None:
        try:
            batch_uuid = uuid.UUID(batch_id)
        except Exception:
            return
        repo = DominationRepository(self.db, table="edi_artifacts")
        batch = repo.get(tenant_id=self.tenant_id, record_id=batch_uuid)
        if not batch:
            return
        claim_ids = (batch.get("data") or {}).get("claim_ids") or []
        status_code = "A2" if accepted else "A6"
        for cid_str in claim_ids:
            try:
                self.db.execute(
                    text(
                        "INSERT INTO claim_status_history "
                        "(claim_id, tenant_id, status_code, status_description, source, effective_date, created_at) "
                        "VALUES (:cid, :tid, :code, :desc, '999', :now, :now) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "cid": cid_str,
                        "tid": str(self.tenant_id),
                        "code": status_code,
                        "desc": _277_STATUS_MAP.get(status_code, status_code),
                        "now": _utcnow(),
                    },
                )
            except Exception:
                pass
        self.db.commit()

    def parse_277(self, x12_text: str) -> dict:
        segments = [s.strip() for s in x12_text.split("~") if s.strip()]
        claim_ids: list[str] = []
        status_codes: list[str] = []
        status_descriptions: list[str] = []
        effective_date: str = ""

        for seg in segments:
            parts = seg.split("*")
            tag = parts[0].strip()
            if tag == "TRN" and len(parts) > 2:
                claim_ids.append(parts[2].strip())
            if tag == "STC" and len(parts) > 1:
                stc_composite = parts[1].strip()
                code = stc_composite.split(":")[0] if ":" in stc_composite else stc_composite
                status_codes.append(code)
                status_descriptions.append(_277_STATUS_MAP.get(code, code))
            if tag == "DTP" and len(parts) > 3 and parts[1].strip() == "472":
                effective_date = parts[3].strip()

        now = _utcnow()
        for i, cid in enumerate(claim_ids):
            code = status_codes[i] if i < len(status_codes) else "A1"
            desc = status_descriptions[i] if i < len(status_descriptions) else code
            try:
                self.db.execute(
                    text(
                        "INSERT INTO claim_status_history "
                        "(claim_id, tenant_id, status_code, status_description, source, effective_date, created_at) "
                        "VALUES (:cid, :tid, :code, :desc, '277', :eff, :now) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "cid": cid,
                        "tid": str(self.tenant_id),
                        "code": code,
                        "desc": desc,
                        "eff": effective_date or now,
                        "now": now,
                    },
                )
            except Exception:
                pass
        self.db.commit()

        return {
            "claim_ids": claim_ids,
            "status_codes": status_codes,
            "status_descriptions": status_descriptions,
            "effective_date": effective_date,
        }

    async def parse_835(self, x12_text: str) -> dict:
        base_result = _parse_835_base(x12_text)

        segments = [s.strip() for s in x12_text.split("~") if s.strip()]
        payment_amount: float = 0.0
        check_number: str = ""
        paid_date: str = ""

        for seg in segments:
            parts = seg.split("*")
            tag = parts[0].strip()
            if tag == "BPR" and len(parts) > 16:
                try:
                    payment_amount = float(parts[2].strip())
                except Exception:
                    pass
                try:
                    paid_date = parts[16].strip()
                except Exception:
                    pass
            if tag == "TRN" and len(parts) > 2:
                check_number = parts[2].strip()

        enriched = {
            **base_result,
            "payment_amount": payment_amount,
            "check_number": check_number,
            "paid_date": paid_date,
        }

        content_b64 = base64.b64encode(x12_text.encode("utf-8")).decode("ascii")
        sha256 = hashlib.sha256(x12_text.encode("utf-8")).hexdigest()

        await self.svc.create(
            table="edi_artifacts",
            tenant_id=self.tenant_id,
            actor_user_id=None,
            data={
                "entity_type": "edi_file",
                "file_type": "835",
                "content_b64": content_b64,
                "sha256": sha256,
                "status": "parsed",
                "payment_amount": payment_amount,
                "check_number": check_number,
                "paid_date": paid_date,
                "denial_count": len(base_result.get("denials", [])),
                "parsed_at": _utcnow(),
            },
            correlation_id=None,
        )

        return enriched

    async def get_claim_explain(self, claim_id: str, ai_service: Any) -> dict:
        try:
            rows = self.db.execute(
                text(
                    "SELECT status_code, status_description, source, effective_date, created_at "
                    "FROM claim_status_history "
                    "WHERE claim_id = :cid AND tenant_id = :tid "
                    "ORDER BY created_at DESC LIMIT 10"
                ),
                {"cid": claim_id, "tid": str(self.tenant_id)},
            ).mappings().all()
            history = [dict(r) for r in rows]
        except Exception:
            history = []

        latest_code = history[0]["status_code"] if history else "UNKNOWN"
        latest_desc = history[0]["status_description"] if history else "No status on record"

        status_summary = (
            f"Claim ID: {claim_id}\n"
            f"Latest Status Code: {latest_code}\n"
            f"Description: {latest_desc}\n"
            f"History ({len(history)} entries):\n"
        )
        for h in history[:5]:
            status_summary += f"  - [{h.get('source', '?')}] {h.get('status_code')} — {h.get('status_description')} ({h.get('effective_date', '')})\n"

        cache_key = hashlib.sha256(status_summary.encode()).hexdigest()[:16]

        try:
            explanation, _meta = ai_service.chat(
                system=(
                    "You are an EMS billing expert. Explain this claim status in plain language "
                    "for a billing coordinator. Be concise, actionable, and specific about what "
                    "next steps should be taken."
                ),
                user=status_summary,
            )
        except Exception as exc:
            explanation = f"AI explanation unavailable: {exc}"

        return {
            "claim_id": claim_id,
            "status_code": latest_code,
            "explanation": explanation,
            "source": "ai",
            "cache_key": cache_key,
        }
