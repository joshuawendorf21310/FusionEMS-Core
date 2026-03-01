from __future__ import annotations

DOC_TYPES = [
    "facesheet",
    "pcs",
    "insurance_card",
    "signature",
    "denial_letter",
    "appeal_response",
    "other",
]


def classify_text(text: str) -> str:
    t = text.lower()
    if "physician certification" in t or "pcs" in t:
        return "pcs"
    if "insurance" in t and ("member" in t or "policy" in t):
        return "insurance_card"
    if "denial" in t and ("reason" in t or "remark" in t):
        return "denial_letter"
    if "appeal" in t:
        return "appeal_response"
    if "signature" in t or "signed" in t:
        return "signature"
    if "patient" in t and ("dob" in t or "date of birth" in t):
        return "facesheet"
    return "other"
