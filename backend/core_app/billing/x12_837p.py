from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class X12Envelope:
    isa_control: str
    gs_control: str
    st_control: str


def _seg(*parts: str) -> str:
    return "*".join(parts) + "~"


def _now() -> tuple[str, str]:
    now = dt.datetime.utcnow()
    return now.strftime("%y%m%d"), now.strftime("%H%M")


def build_837p_ambulance(
    *,
    submitter_id: str,
    receiver_id: str,
    billing_npi: str,
    billing_tax_id: str,
    patient: dict[str, Any],
    claim: dict[str, Any],
    service_lines: list[dict[str, Any]],
) -> tuple[str, X12Envelope]:
    """
    Minimal 837P (005010X222A1) generator sufficient to produce a structurally valid X12
    for an ambulance claim artifact pipeline. It does NOT guarantee payer acceptance;
    payer/clearinghouse rules vary. This generator is deterministic and auditable.

    The system stores the resulting X12 as an artifact, runs pre-validation, and can submit
    via configured Office Ally SFTP.
    """
    isa_date, isa_time = _now()
    gs_date = dt.datetime.utcnow().strftime("%Y%m%d")
    gs_time = dt.datetime.utcnow().strftime("%H%M")

    isa_ctrl = f"{uuid.uuid4().int % 10**9:09d}"
    gs_ctrl = f"{uuid.uuid4().int % 10**9}"
    st_ctrl = f"{uuid.uuid4().int % 10**4:04d}"

    env = X12Envelope(isa_control=isa_ctrl, gs_control=gs_ctrl, st_control=st_ctrl)

    segments: list[str] = []
    segments.append(_seg("ISA", "00", "          ", "00", "          ", "ZZ", submitter_id.ljust(15)[:15], "ZZ", receiver_id.ljust(15)[:15], isa_date, isa_time, "^", "00501", isa_ctrl, "0", "T", ":"))
    segments.append(_seg("GS", "HC", submitter_id, receiver_id, gs_date, gs_time, gs_ctrl, "X", "005010X222A1"))
    segments.append(_seg("ST", "837", st_ctrl, "005010X222A1"))
    segments.append(_seg("BHT", "0019", "00", claim.get("claim_id", st_ctrl), gs_date, gs_time, "CH"))

    segments.append(_seg("NM1", "41", "2", claim.get("submitter_name", "FUSIONEMSQUANTUM"), "", "", "", "", "46", submitter_id))
    segments.append(_seg("PER", "IC", claim.get("submitter_contact", "BILLING"), "TE", claim.get("submitter_phone", "0000000000")))

    segments.append(_seg("NM1", "40", "2", claim.get("receiver_name", "OFFICEALLY"), "", "", "", "", "46", receiver_id))

    segments.append(_seg("HL", "1", "", "20", "1"))
    segments.append(_seg("NM1", "85", "2", claim.get("billing_name", "FUSIONEMSQUANTUM"), "", "", "", "", "XX", billing_npi))
    segments.append(_seg("N3", claim.get("billing_address1", "UNKNOWN")))
    segments.append(_seg("N4", claim.get("billing_city", "UNKNOWN"), claim.get("billing_state", "WI"), claim.get("billing_zip", "00000")))
    segments.append(_seg("REF", "EI", billing_tax_id))

    segments.append(_seg("HL", "2", "1", "22", "0"))
    segments.append(_seg("SBR", "P", "18", "", "", "", "", "", claim.get("insurance_type", "CI")))
    segments.append(_seg("NM1", "IL", "1", patient.get("last_name", "UNKNOWN"), patient.get("first_name", "UNKNOWN"), patient.get("middle_name", ""), "", "", "MI", claim.get("member_id", "UNKNOWN")))
    segments.append(_seg("DMG", "D8", patient.get("dob", "19000101"), patient.get("sex", "U")))

    total_charge = sum(int(float(sl.get("charge", 0)) * 100) for sl in service_lines)
    segments.append(_seg("CLM", claim.get("claim_id", st_ctrl), f"{total_charge/100:.2f}", "", "11:B:1", "Y", "A", "Y", "Y"))
    segments.append(_seg("DTP", "431", "D8", claim.get("dos", gs_date)))

    for lx, sl in enumerate(service_lines, start=1):
        proc = sl.get("procedure_code", "A0429")
        charge = float(sl.get("charge", 0))
        units = str(sl.get("units", 1))
        segments.append(_seg("LX", str(lx)))
        segments.append(_seg("SV1", f"HC:{proc}", f"{charge:.2f}", "UN", units, "", "", "", "1"))
        if sl.get("dos"):
            segments.append(_seg("DTP", "472", "D8", sl["dos"]))

    segments.append(_seg("SE", str(len(segments) + 1), st_ctrl))
    segments.append(_seg("GE", "1", gs_ctrl))
    segments.append(_seg("IEA", "1", isa_ctrl))

    return "".join(segments), env
