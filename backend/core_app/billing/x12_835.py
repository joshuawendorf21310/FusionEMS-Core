from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EraDenial:
    claim_id: str
    group_code: str
    reason_code: str
    amount: float


def parse_835(x12_text: str) -> dict[str, Any]:
    """
    Minimal 835 parser: extracts CLP (claim payment info) and CAS (adjustments/denials)
    to populate `eras` and `denials`. This is deterministic and safe; it does not attempt
    full EDI normalization.
    """
    segments = [s for s in x12_text.split("~") if s.strip()]
    current_claim_id: str | None = None
    denials: list[EraDenial] = []
    for seg in segments:
        parts = seg.split("*")
        tag = parts[0].strip()
        if tag == "CLP" and len(parts) > 2:
            current_claim_id = parts[1]
        if tag == "CAS" and current_claim_id and len(parts) >= 4:
            # CAS*<group>*<reason>*<amount>*...
            group = parts[1]
            reason = parts[2]
            try:
                amt = float(parts[3])
            except Exception:
                amt = 0.0
            denials.append(EraDenial(claim_id=current_claim_id, group_code=group, reason_code=reason, amount=amt))
    return {"denials": [d.__dict__ for d in denials]}
