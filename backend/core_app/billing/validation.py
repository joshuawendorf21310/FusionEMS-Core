from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository


class BillingValidator:
    """Deterministic, fast validation for billing cases.
    Produces missing-doc tasks and a risk score (rule-based).
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.repo_cases = DominationRepository(db, table="billing_cases")
        self.repo_docs = DominationRepository(db, table="documents")
        self.repo_tasks = DominationRepository(db, table="missing_document_tasks")

    def validate_case(self, case_id: uuid.UUID) -> dict[str, Any]:
        case = self.repo_cases.get(self.tenant_id, case_id)
        if not case:
            raise ValueError("billing_case_not_found")
        data = case["data"]
        required_docs = data.get("required_docs") or ["facesheet", "pcs", "signature"]
        attached_doc_ids = set(data.get("attached_document_ids") or [])
        # infer attachments from documents table as well
        docs = self.repo_docs.list(self.tenant_id, limit=2000)
        for d in docs:
            dd = d["data"]
            if dd.get("owner_entity_type") == "billing_case" and dd.get("owner_entity_id") == str(case_id):
                attached_doc_ids.add(str(d["id"]))

        # compute missing by doc_type presence
        have_types = set()
        for d in docs:
            dd = d["data"]
            if dd.get("owner_entity_type") == "billing_case" and dd.get("owner_entity_id") == str(case_id):
                if dd.get("doc_type"):
                    have_types.add(dd["doc_type"])

        missing = [t for t in required_docs if t not in have_types]
        risk = 0.05
        risk_flags: list[str] = []
        if missing:
            risk += min(0.6, 0.2 * len(missing))
            risk_flags.append("MISSING_REQUIRED_DOCUMENTS")
        if not data.get("icd10_codes"):
            risk += 0.15
            risk_flags.append("MISSING_ICD10")
        if data.get("mileage") is None:
            risk += 0.1
            risk_flags.append("MISSING_MILEAGE")

        return {"case": case, "missing_docs": missing, "risk_score": round(min(risk, 0.99), 2), "risk_flags": risk_flags}
