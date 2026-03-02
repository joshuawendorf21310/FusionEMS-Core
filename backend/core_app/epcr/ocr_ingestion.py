from __future__ import annotations

import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3

from core_app.documents.s3_storage import put_bytes

_TEXTRACT_POLL_INTERVAL_S = 5
_TEXTRACT_MAX_POLLS = 60


class EPCROcrService:
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self.textract = boto3.client("textract")

    def ingest_facesheet(
        self,
        content: bytes,
        filename: str,
        chart_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        key = f"epcr/{tenant_id}/{chart_id}/ocr/{uuid.uuid4()}_{filename}"
        put_bytes(bucket=self.bucket, key=key, content=content)

        start_resp = self.textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": self.bucket, "Name": key}}
        )
        job_id: str = start_resp["JobId"]
        raw_text = self._poll_textract(job_id)

        parsed_fields = self._parse_facesheet_fields(raw_text)
        review_items = [
            {"field": k, "value": v["value"], "confidence": v["confidence"]}
            for k, v in parsed_fields.items()
            if v["value"]
        ]
        return {
            "ocr_job_id": str(uuid.uuid4()),
            "s3_key": key,
            "raw_text": raw_text,
            "extracted_fields": parsed_fields,
            "review_items": review_items,
            "review_count": len([v for v in parsed_fields.values() if v["value"]]),
            "status": "completed",
            "processed_at": datetime.now(UTC).isoformat(),
        }

    def _parse_facesheet_fields(self, text: str) -> dict[str, Any]:
        def _find(patterns: list[str], text: str) -> tuple[str, float]:
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if m:
                    val = (
                        m.group(1).strip()
                        if m.lastindex and m.lastindex >= 1
                        else m.group(0).strip()
                    )
                    return val, 0.8
            for pattern in patterns:
                m = re.search(pattern.split(r"\s")[0], text, re.IGNORECASE)
                if m:
                    return m.group(0).strip(), 0.4
            return "", 0.0

        def _make(value: str, confidence: float) -> dict[str, Any]:
            return {"value": value, "confidence": confidence}

        name_val, name_conf = _find(
            [r"(?:Patient|Name):\s*([A-Za-z ,'-]+)", r"Patient Name:\s*(.+)"],
            text,
        )
        dob_val, dob_conf = _find(
            [r"(?:DOB|Date of Birth):\s*(\d{1,2}/\d{1,2}/\d{4})"],
            text,
        )
        mrn_val, mrn_conf = _find(
            [r"(?:MRN|Medical Record(?:\s*Number|#)?):\s*([A-Za-z0-9-]+)"],
            text,
        )
        ins_id_val, ins_id_conf = _find(
            [r"(?:Member ID|Policy(?:\s*#)?):\s*([A-Za-z0-9-]+)"],
            text,
        )
        ins_payer_val, ins_payer_conf = _find(
            [r"(?:Insurance|Payer):\s*(.+)"],
            text,
        )
        addr_val, addr_conf = _find(
            [r"Address:\s*(.+)"],
            text,
        )
        phone_m = re.search(r"\b(\d{3}[-.\s]\d{3}[-.\s]\d{4})\b", text)
        phone_val = phone_m.group(1).strip() if phone_m else ""
        phone_conf = 0.8 if phone_m else 0.0

        return {
            "patient_name": _make(name_val, name_conf),
            "dob": _make(dob_val, dob_conf),
            "mrn": _make(mrn_val, mrn_conf),
            "insurance_id": _make(ins_id_val, ins_id_conf),
            "insurance_payer": _make(ins_payer_val, ins_payer_conf),
            "address": _make(addr_val, addr_conf),
            "phone": _make(phone_val, phone_conf),
        }

    def ingest_transport_paperwork(
        self,
        content: bytes,
        filename: str,
        chart_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        key = f"epcr/{tenant_id}/{chart_id}/ocr/{uuid.uuid4()}_{filename}"
        put_bytes(bucket=self.bucket, key=key, content=content)

        start_resp = self.textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": self.bucket, "Name": key}}
        )
        job_id: str = start_resp["JobId"]
        raw_text = self._poll_textract(job_id)

        parsed_fields = self._parse_transport_fields(raw_text)
        review_items = [
            {"field": k, "value": v, "confidence": None} for k, v in parsed_fields.items() if v
        ]
        return {
            "ocr_job_id": str(uuid.uuid4()),
            "s3_key": key,
            "raw_text": raw_text,
            "extracted_fields": parsed_fields,
            "review_items": review_items,
            "review_count": len([v for v in parsed_fields.values() if v]),
            "status": "completed",
            "paperwork_type": "transport",
            "processed_at": datetime.now(UTC).isoformat(),
        }

    def _parse_transport_fields(self, text: str) -> dict[str, Any]:
        _DRUG_PATTERN = re.compile(
            r"\b(epinephrine|morphine|fentanyl|midazolam|lorazepam|dopamine|norepinephrine|"
            r"amiodarone|lidocaine|atropine|adenosine|naloxone|dextrose|normal saline|NS|"
            r"lactated ringer|LR)\b.*?(\d+[\.,]?\d*\s*(?:mg|mcg|g|mEq|units|mL))",
            re.IGNORECASE,
        )
        _BP_PATTERN = re.compile(r"\b(?:BP|Blood Pressure)[:\s]*(\d{2,3}/\d{2,3})\b", re.IGNORECASE)
        _HR_PATTERN = re.compile(r"\b(?:HR|Heart Rate|Pulse)[:\s]*(\d{2,3})\b", re.IGNORECASE)
        _SPO2_PATTERN = re.compile(r"\b(?:SpO2|O2 Sat|Oxygen)[:\s]*(\d{2,3})%?\b", re.IGNORECASE)
        _PROC_PATTERN = re.compile(
            r"\b(intubation|intubated|RSI|IV access|IO access|CPR|defibrillation|cardioversion|"
            r"chest compression|cricothyrotomy|thoracostomy|pacing|cardioverted|defibrillated)\b",
            re.IGNORECASE,
        )

        prior_meds: list[dict[str, Any]] = []
        for m in _DRUG_PATTERN.finditer(text):
            prior_meds.append(
                {"value": m.group(0).strip(), "confidence": 0.8, "flagged_prior": True}
            )

        prior_vitals: list[dict[str, Any]] = []
        for m in _BP_PATTERN.finditer(text):
            prior_vitals.append(
                {"value": f"BP {m.group(1)}", "confidence": 0.8, "flagged_prior": True}
            )
        for m in _HR_PATTERN.finditer(text):
            prior_vitals.append(
                {"value": f"HR {m.group(1)}", "confidence": 0.8, "flagged_prior": True}
            )
        for m in _SPO2_PATTERN.finditer(text):
            prior_vitals.append(
                {"value": f"SpO2 {m.group(1)}%", "confidence": 0.8, "flagged_prior": True}
            )

        prior_procs: list[dict[str, Any]] = []
        seen_procs: set[str] = set()
        for m in _PROC_PATTERN.finditer(text):
            val = m.group(0).strip().lower()
            if val not in seen_procs:
                seen_procs.add(val)
                prior_procs.append(
                    {"value": m.group(0).strip(), "confidence": 0.8, "flagged_prior": True}
                )

        return {
            "prior_medications": prior_meds,
            "prior_vitals": prior_vitals,
            "prior_procedures": prior_procs,
        }

    def _poll_textract(self, job_id: str) -> str:
        lines: list[str] = []
        next_token: str | None = None

        for _attempt in range(_TEXTRACT_MAX_POLLS):
            time.sleep(_TEXTRACT_POLL_INTERVAL_S)
            try:
                kwargs: dict[str, Any] = {"JobId": job_id}
                if next_token:
                    kwargs["NextToken"] = next_token
                resp = self.textract.get_document_text_detection(**kwargs)
            except Exception:
                return ""

            job_status: str = resp.get("JobStatus", "")

            if job_status == "FAILED":
                return ""

            if job_status == "SUCCEEDED":
                for block in resp.get("Blocks", []):
                    if block.get("BlockType") == "LINE":
                        lines.append(block.get("Text", ""))
                next_token = resp.get("NextToken")
                if not next_token:
                    break
        else:
            return ""

        return "\n".join(lines)
