from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationEntry:
    stripe_id: str
    local_id: str
    amount_stripe: int
    amount_local: int
    status_stripe: str
    status_local: str
    match: bool
    discrepancy: Optional[str] = None


@dataclass
class ReconciliationReport:
    run_id: str = ""
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_checked: int = 0
    matched: int = 0
    mismatched: int = 0
    missing_local: int = 0
    missing_stripe: int = 0
    entries: list[ReconciliationEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_at": self.run_at,
            "total_checked": self.total_checked,
            "matched": self.matched,
            "mismatched": self.mismatched,
            "missing_local": self.missing_local,
            "missing_stripe": self.missing_stripe,
            "entries": [
                {
                    "stripe_id": e.stripe_id,
                    "local_id": e.local_id,
                    "amount_stripe": e.amount_stripe,
                    "amount_local": e.amount_local,
                    "match": e.match,
                    "discrepancy": e.discrepancy,
                }
                for e in self.entries
                if not e.match
            ],
        }


class StripeReconciliation:
    def __init__(self, db_service=None, stripe_client=None):
        self._db = db_service
        self._stripe = stripe_client

    def reconcile_invoices(
        self,
        tenant_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ReconciliationReport:
        import uuid
        report = ReconciliationReport(run_id=str(uuid.uuid4()))

        stripe_invoices = self._fetch_stripe_invoices(start_date, end_date)
        local_invoices = self._fetch_local_invoices(tenant_id, start_date, end_date)

        local_map = {inv.get("stripe_invoice_id"): inv for inv in local_invoices if inv.get("stripe_invoice_id")}

        for s_inv in stripe_invoices:
            report.total_checked += 1
            s_id = s_inv.get("id", "")
            s_amount = s_inv.get("amount_paid", 0)
            s_status = s_inv.get("status", "")

            local = local_map.pop(s_id, None)
            if local is None:
                report.missing_local += 1
                report.entries.append(ReconciliationEntry(
                    stripe_id=s_id, local_id="", amount_stripe=s_amount, amount_local=0,
                    status_stripe=s_status, status_local="missing", match=False,
                    discrepancy="Invoice exists in Stripe but not in local database",
                ))
                continue

            l_amount = local.get("amount", 0)
            l_status = local.get("status", "")
            match = (s_amount == l_amount) and (s_status == l_status)

            if match:
                report.matched += 1
            else:
                report.mismatched += 1

            report.entries.append(ReconciliationEntry(
                stripe_id=s_id, local_id=local.get("id", ""),
                amount_stripe=s_amount, amount_local=l_amount,
                status_stripe=s_status, status_local=l_status,
                match=match,
                discrepancy=None if match else f"Amount: {s_amount} vs {l_amount}, Status: {s_status} vs {l_status}",
            ))

        for remaining_id, local in local_map.items():
            report.total_checked += 1
            report.missing_stripe += 1
            report.entries.append(ReconciliationEntry(
                stripe_id=remaining_id or "", local_id=local.get("id", ""),
                amount_stripe=0, amount_local=local.get("amount", 0),
                status_stripe="missing", status_local=local.get("status", ""),
                match=False,
                discrepancy="Invoice exists locally but not found in Stripe",
            ))

        logger.info(
            "reconciliation_complete run_id=%s total=%d matched=%d mismatched=%d",
            report.run_id, report.total_checked, report.matched, report.mismatched,
        )

        return report

    def _fetch_stripe_invoices(self, start_date=None, end_date=None) -> list[dict]:
        try:
            import stripe as stripe_lib
            params: dict = {"limit": 100}
            if start_date:
                params["created"] = {"gte": int(datetime.fromisoformat(start_date).timestamp())}
            invoices = stripe_lib.Invoice.list(**params)
            return [inv.to_dict() for inv in invoices.auto_paging_iter()]
        except Exception:
            logger.exception("stripe_fetch_invoices_failed")
            return []

    def _fetch_local_invoices(self, tenant_id: str, start_date=None, end_date=None) -> list[dict]:
        if self._db is None:
            return []
        try:
            return self._db.list_invoices(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        except Exception:
            logger.exception("local_fetch_invoices_failed")
            return []
