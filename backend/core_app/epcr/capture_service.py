from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any

from core_app.documents.s3_storage import put_bytes


class CaptureService:
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def process_rhythm_strip(
        self,
        content: bytes,
        filename: str,
        chart_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        self._detect_content_type(content)
        key = f"epcr/{tenant_id}/{chart_id}/captures/rhythm/{uuid.uuid4()}_{filename}"
        sha256 = self._compute_sha256(content)
        enhanced = False

        try:
            from PIL import Image, ImageEnhance
            img = Image.open(io.BytesIO(content)).convert("L")
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = img.crop(img.getbbox())
            buf = io.BytesIO()
            fmt = "PNG" if filename.lower().endswith(".png") else "JPEG"
            img.save(buf, format=fmt)
            content = buf.getvalue()
            enhanced = True
        except ImportError:
            pass

        content_type = self._detect_content_type(content)
        put_bytes(bucket=self.bucket, key=key, content=content, content_type=content_type)

        return {
            "capture_id": str(uuid.uuid4()),
            "capture_type": "rhythm_strip",
            "s3_key": key,
            "filename": filename,
            "size_bytes": len(content),
            "sha256": sha256,
            "enhanced": enhanced,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "attachment_type": "rhythm_strip",
        }

    def process_pump_screen(
        self,
        content: bytes,
        filename: str,
        chart_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        key = f"epcr/{tenant_id}/{chart_id}/captures/pump/{uuid.uuid4()}_{filename}"
        sha256 = self._compute_sha256(content)
        content_type = self._detect_content_type(content)
        put_bytes(bucket=self.bucket, key=key, content=content, content_type=content_type)

        extracted_fields: dict[str, Any] = {}
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img)
            extracted_fields = _parse_pump_text(text)
        except ImportError:
            pass

        return {
            "capture_id": str(uuid.uuid4()),
            "capture_type": "pump_screen",
            "s3_key": key,
            "filename": filename,
            "size_bytes": len(content),
            "sha256": sha256,
            "enhanced": False,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "attachment_type": "pump_screen",
            "extracted_fields": extracted_fields,
        }

    def process_vent_screen(
        self,
        content: bytes,
        filename: str,
        chart_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        key = f"epcr/{tenant_id}/{chart_id}/captures/vent/{uuid.uuid4()}_{filename}"
        sha256 = self._compute_sha256(content)
        content_type = self._detect_content_type(content)
        put_bytes(bucket=self.bucket, key=key, content=content, content_type=content_type)

        extracted_fields: dict[str, Any] = {}
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img)
            extracted_fields = _parse_vent_text(text)
        except ImportError:
            pass

        return {
            "capture_id": str(uuid.uuid4()),
            "capture_type": "vent_screen",
            "s3_key": key,
            "filename": filename,
            "size_bytes": len(content),
            "sha256": sha256,
            "enhanced": False,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "attachment_type": "vent_screen",
            "extracted_fields": extracted_fields,
        }

    def _detect_content_type(self, content: bytes) -> str:
        if content[:4] == b"%PDF":
            return "application/pdf"
        if content[:4] == b"\x89PNG":
            return "image/png"
        if content[:2] == b"\xff\xd8":
            return "image/jpeg"
        if content[:4] == b"GIF8":
            return "image/gif"
        return "application/octet-stream"

    def _compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


def _parse_pump_text(text: str) -> dict[str, Any]:
    import re
    fields: dict[str, Any] = {}
    drug_m = re.search(r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:infusion|drip|gtt)\b", text, re.IGNORECASE)
    if drug_m:
        fields["drug_name"] = drug_m.group(1).strip()
    conc_m = re.search(r"(\d+[\.,]?\d*)\s*(?:mg|mcg|g)/(?:\d+\s*)?mL", text, re.IGNORECASE)
    if conc_m:
        fields["concentration"] = conc_m.group(0).strip()
    rate_m = re.search(r"(?:Rate|mL/hr|mL/h)[:\s]*(\d+[\.,]?\d*)", text, re.IGNORECASE)
    if rate_m:
        fields["rate"] = rate_m.group(1).strip()
    vol_m = re.search(r"(?:VTBI|Vol(?:ume)?\s+Infused)[:\s]*(\d+[\.,]?\d*)\s*mL", text, re.IGNORECASE)
    if vol_m:
        fields["volume_infused"] = vol_m.group(1).strip()
    return fields


def _parse_vent_text(text: str) -> dict[str, Any]:
    import re
    fields: dict[str, Any] = {}
    mode_m = re.search(r"(?:Mode|Vent\s+Mode)[:\s]*([A-Z/]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
    if mode_m:
        fields["mode"] = mode_m.group(1).strip()
    fio2_m = re.search(r"(?:FiO2|O2%)[:\s]*(\d+)%?", text, re.IGNORECASE)
    if fio2_m:
        fields["fio2"] = fio2_m.group(1).strip()
    peep_m = re.search(r"PEEP[:\s]*(\d+[\.,]?\d*)", text, re.IGNORECASE)
    if peep_m:
        fields["peep"] = peep_m.group(1).strip()
    tv_m = re.search(r"(?:TV|Tidal\s+Vol(?:ume)?)[:\s]*(\d+[\.,]?\d*)\s*(?:mL)?", text, re.IGNORECASE)
    if tv_m:
        fields["tidal_volume"] = tv_m.group(1).strip()
    rate_m = re.search(r"(?:Rate|RR|Resp\s+Rate)[:\s]*(\d+)", text, re.IGNORECASE)
    if rate_m:
        fields["rate"] = rate_m.group(1).strip()
    pip_m = re.search(r"(?:PIP|Peak\s+Insp(?:iratory)?)[:\s]*(\d+[\.,]?\d*)", text, re.IGNORECASE)
    if pip_m:
        fields["pip"] = pip_m.group(1).strip()
    return fields
