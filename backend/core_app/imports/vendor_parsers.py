from __future__ import annotations

import csv
import io
from typing import Any
from xml.etree import ElementTree as ET


VENDOR_SIGNATURES = {
    "imagetrend": ["PCRNumber", "UnitCallSign", "AgencyName", "IncidentNumber", "CADIncidentNumber"],
    "eso": ["Incident_Number", "Unit_Number", "Patient_Last_Name", "ESO_ID", "RunNumber"],
    "zoll": ["IncidentID", "ZollAgencyID", "PCR_ID", "RunNumber", "Unit"],
    "traumasoft": ["TSSRunNumber", "TSPatientID", "TSAgencyID", "TSSIncidentID"],
}


def detect_vendor(headers: list[str]) -> str:
    headers_upper = {h.upper() for h in headers}
    scores: dict[str, int] = {}
    for vendor, sigs in VENDOR_SIGNATURES.items():
        score = sum(1 for s in sigs if s.upper() in headers_upper)
        if score > 0:
            scores[vendor] = score
    if not scores:
        return "unknown"
    return max(scores, key=lambda k: scores[k])


def _normalize_imagetrend_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "incident_number": row.get("PCRNumber") or row.get("IncidentNumber") or row.get("CADIncidentNumber"),
        "unit_number": row.get("UnitCallSign") or row.get("Unit"),
        "patient_last_name": row.get("PatientLastName") or row.get("LastName"),
        "patient_first_name": row.get("PatientFirstName") or row.get("FirstName"),
        "date_of_birth": row.get("DateOfBirth") or row.get("PatientDOB"),
        "dispatch_time": row.get("DispatchTime") or row.get("TimeDispatched"),
        "arrived_scene_time": row.get("ArrivalTime") or row.get("TimeOnScene"),
        "patient_contact_time": row.get("PatientContactTime") or row.get("TimePatientContact"),
        "transport_destination": row.get("DestinationName") or row.get("Hospital"),
        "primary_impression": row.get("PrimaryImpression") or row.get("ChiefComplaint"),
        "billed_amount": row.get("BilledAmount") or row.get("ChargeAmount"),
        "payer_type": row.get("PayerType") or row.get("InsuranceType"),
        "icd10_codes": row.get("DiagnosisCodes", ""),
        "_source_vendor": "imagetrend",
        "_raw": dict(row),
    }


def _normalize_eso_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "incident_number": row.get("Incident_Number") or row.get("RunNumber"),
        "unit_number": row.get("Unit_Number"),
        "patient_last_name": row.get("Patient_Last_Name"),
        "patient_first_name": row.get("Patient_First_Name"),
        "date_of_birth": row.get("Patient_DOB"),
        "dispatch_time": row.get("Dispatch_Time"),
        "arrived_scene_time": row.get("Scene_Arrival_Time"),
        "primary_impression": row.get("Chief_Complaint") or row.get("Impression"),
        "billed_amount": row.get("Billed_Amount"),
        "payer_type": row.get("Primary_Insurance_Type"),
        "_source_vendor": "eso",
        "_raw": dict(row),
    }


def _normalize_zoll_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "incident_number": row.get("IncidentID") or row.get("PCR_ID"),
        "unit_number": row.get("Unit"),
        "patient_last_name": row.get("PatientLastName"),
        "patient_first_name": row.get("PatientFirstName"),
        "dispatch_time": row.get("DispatchDT"),
        "arrived_scene_time": row.get("ArriveSceneDT"),
        "primary_impression": row.get("PrimaryImpression"),
        "billed_amount": row.get("TotalCharge"),
        "payer_type": row.get("InsuranceCarrier"),
        "_source_vendor": "zoll",
        "_raw": dict(row),
    }


def _normalize_traumasoft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "incident_number": row.get("TSSRunNumber") or row.get("TSSIncidentID"),
        "unit_number": row.get("TSUnit"),
        "patient_last_name": row.get("TSPatLastName"),
        "patient_first_name": row.get("TSPatFirstName"),
        "date_of_birth": row.get("TSPatDOB"),
        "dispatch_time": row.get("TSDispatchTime"),
        "arrived_scene_time": row.get("TSArriveScene"),
        "billed_amount": row.get("TSBilledAmount"),
        "_source_vendor": "traumasoft",
        "_raw": dict(row),
    }


VENDOR_NORMALIZERS = {
    "imagetrend": _normalize_imagetrend_row,
    "eso": _normalize_eso_row,
    "zoll": _normalize_zoll_row,
    "traumasoft": _normalize_traumasoft_row,
}


def parse_vendor_csv(content: bytes, vendor_hint: str | None = None) -> dict[str, Any]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"vendor": "unknown", "records": [], "total": 0, "headers": []}

    headers = list(rows[0].keys()) if rows else []
    vendor = vendor_hint or detect_vendor(headers)
    normalizer = VENDOR_NORMALIZERS.get(vendor)

    records = []
    for row in rows:
        if normalizer:
            normalized = normalizer(row)
        else:
            normalized = {"_source_vendor": vendor, "_raw": dict(row), **dict(row)}
        records.append(normalized)

    return {"vendor": vendor, "records": records, "total": len(records), "headers": headers}


def parse_vendor_xml(content: bytes, vendor_hint: str | None = None) -> dict[str, Any]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {"error": str(e), "vendor": "unknown", "records": []}

    records = []
    vendor = vendor_hint or "xml_unknown"

    for child in root:
        row: dict[str, Any] = {}
        for elem in child:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            row[tag] = elem.text
        if row:
            records.append({"_source_vendor": vendor, "_raw": dict(row), **row})

    return {"vendor": vendor, "records": records, "total": len(records)}


def score_import_completeness(records: list[dict[str, Any]]) -> dict[str, Any]:
    required_fields = [
        "incident_number", "unit_number", "patient_last_name", "patient_first_name",
        "dispatch_time", "arrived_scene_time", "primary_impression", "billed_amount",
    ]
    recommended_fields = [
        "date_of_birth", "payer_type", "patient_contact_time", "transport_destination",
        "icd10_codes",
    ]
    denial_risk_fields = [
        "icd10_codes", "payer_type", "date_of_birth", "billed_amount",
    ]

    total = len(records)
    if total == 0:
        return {"total_records": 0, "completeness_pct": 0, "denial_risk": "unknown"}

    field_fill: dict[str, int] = {f: 0 for f in required_fields + recommended_fields}
    for rec in records:
        for f in field_fill:
            if rec.get(f):
                field_fill[f] += 1

    req_score = sum(field_fill[f] for f in required_fields) / (len(required_fields) * total) * 100
    rec_score = sum(field_fill[f] for f in recommended_fields) / (len(recommended_fields) * total) * 100
    overall_score = (req_score * 0.7) + (rec_score * 0.3)

    denial_missing_pct = sum(
        1 for rec in records
        if any(not rec.get(f) for f in denial_risk_fields)
    ) / total * 100

    denial_risk = "low" if denial_missing_pct < 10 else "medium" if denial_missing_pct < 30 else "high"

    return {
        "total_records": total,
        "completeness_pct": round(overall_score, 1),
        "required_completeness_pct": round(req_score, 1),
        "recommended_completeness_pct": round(rec_score, 1),
        "denial_risk": denial_risk,
        "denial_risk_pct": round(denial_missing_pct, 1),
        "field_fill_rates": {f: round(field_fill[f]/total*100, 1) for f in field_fill},
        "missing_critical_fields": [
            f for f in required_fields if field_fill.get(f, 0) / total < 0.5
        ],
    }
