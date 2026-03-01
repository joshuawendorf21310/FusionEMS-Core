from __future__ import annotations

import uuid

from core_app.billing.validation import BillingValidator


class FakeRepo:
    def __init__(self, item=None, items=None):
        self._item = item
        self._items = items or []
    def get(self, tenant_id, id_):
        return self._item
    def list(self, tenant_id, limit=100):
        return self._items
    def create(self, tenant_id, data):
        return {"id": uuid.uuid4(), "data": data}


class FakeDB:
    pass


def test_validate_case_missing_docs_increases_risk(monkeypatch):
    tenant_id = uuid.uuid4()
    case_id = uuid.uuid4()
    case = {"id": case_id, "data": {"required_docs": ["facesheet","pcs"], "icd10_codes": ["A00"], "mileage": 10}}

    v = BillingValidator(db=FakeDB(), tenant_id=tenant_id)
    # monkeypatch repos
    v.repo_cases = FakeRepo(item=case)
    v.repo_docs = FakeRepo(items=[])  # no docs -> missing
    v.repo_tasks = FakeRepo(items=[])

    res = v.validate_case(case_id)
    assert res["missing_docs"] == ["facesheet","pcs"]
    assert res["risk_score"] >= 0.4
    assert "MISSING_REQUIRED_DOCUMENTS" in res["risk_flags"]
