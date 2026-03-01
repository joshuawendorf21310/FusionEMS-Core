from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

PHI_PATTERNS = [
    # SSN — with or without dashes
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{9}\b"),
    # Date of birth — labeled or standalone date formats
    re.compile(
        r"\b(?:DOB|date[\s_]of[\s_]birth|birth[\s_]date)\s*:?\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:born|dob)\s*:?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}",
        re.IGNORECASE,
    ),
    # Phone numbers
    re.compile(r"\b(?:\+1[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}\b"),
    # Email addresses
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    # Medicare/Medicaid beneficiary numbers (MBIs — 11 char alphanumeric)
    re.compile(r"\b[1-9][A-Z][A-Z0-9][0-9][A-Z][A-Z0-9][0-9][A-Z]{2}[0-9]{2}\b"),
    # NPI numbers
    re.compile(r"\bNPI\s*:?\s*\d{10}\b", re.IGNORECASE),
    # MRN-like identifiers
    re.compile(
        r"\b(?:MRN|mrn|medical[\s_]record[\s_]number)\s*:?\s*[A-Z0-9\-]{4,20}", re.IGNORECASE
    ),
    re.compile(r"\b[A-Z]{2}\d{6,}\b"),
    # Health plan member IDs (common formats)
    re.compile(r"\b[A-Z]{3}\d{9}\b"),
    # IP addresses
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    # Zip codes (5+4 format — can be geographic identifier)
    re.compile(r"\b\d{5}-\d{4}\b"),
    # Street addresses
    re.compile(
        r"\b\d{1,5}\s+[A-Z][a-z]+\s+(?:St|Ave|Rd|Blvd|Dr|Ln|Ct|Way|Pl|Circle|Court|Drive|Street|Avenue|Road|Boulevard)\b",
        re.IGNORECASE,
    ),
    # Device serial numbers (common patterns)
    re.compile(r"\b(?:SN|S/N|serial)\s*[:\-]?\s*[A-Z0-9\-]{6,20}\b", re.IGNORECASE),
    # Account numbers
    re.compile(
        r"\b(?:account|acct|account[\s_]no|account[\s_]number)\s*[:#]?\s*\d{4,20}\b", re.IGNORECASE
    ),
    # Credit card numbers (16-digit blocks)
    re.compile(r"\b(?:\d{4}[\s\-]){3}\d{4}\b"),
]

FINANCIAL_MUTATION_PATTERNS = [
    re.compile(
        r"(?:change|modify|update|set|alter)\s+(?:amount|payment|charge|fee|balance|rate)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:submit|file|send)\s+(?:claim|bill|invoice)", re.IGNORECASE),
    re.compile(r"(?:delete|remove|void|cancel)\s+(?:claim|payment|charge)", re.IGNORECASE),
]

CLAIM_SUBMISSION_PATTERNS = [
    re.compile(r"submit\s+(?:the\s+)?claim", re.IGNORECASE),
    re.compile(r"file\s+(?:the\s+)?claim", re.IGNORECASE),
    re.compile(r"send\s+(?:the\s+)?(?:837|claim|edi)", re.IGNORECASE),
]


def contains_phi(text: str) -> bool:
    return any(pattern.search(text) for pattern in PHI_PATTERNS)


def contains_financial_mutation(text: str) -> bool:
    return any(pattern.search(text) for pattern in FINANCIAL_MUTATION_PATTERNS)


def contains_claim_submission(text: str) -> bool:
    return any(pattern.search(text) for pattern in CLAIM_SUBMISSION_PATTERNS)


class AiOutput(BaseModel):
    content: str
    task_type: str = "general"
    metadata: dict[str, Any] = {}

    @field_validator("content")
    @classmethod
    def no_phi_in_output(cls, v: str) -> str:
        if contains_phi(v):
            raise ValueError("AI output contains potential PHI — blocked by guardrail")
        return v

    @model_validator(mode="after")
    def no_financial_mutations(self) -> AiOutput:
        if self.task_type in ("billing", "claim", "payment"):
            if contains_financial_mutation(self.content):
                raise ValueError(
                    "AI output contains financial mutation instruction — blocked by guardrail"
                )
            if contains_claim_submission(self.content):
                raise ValueError(
                    "AI output contains autonomous claim submission — blocked by guardrail"
                )
        return self


class AiBillingDraftOutput(BaseModel):
    draft_text: str
    estimated_amount: str | None = None
    appeal_codes: list[str] = []
    requires_human_review: bool = True

    @field_validator("draft_text")
    @classmethod
    def no_phi(cls, v: str) -> str:
        if contains_phi(v):
            raise ValueError("Draft contains potential PHI — use portal links only")
        return v

    @field_validator("estimated_amount")
    @classmethod
    def amount_readonly(cls, v: str | None) -> str | None:
        return v

    @model_validator(mode="after")
    def enforce_human_review(self) -> AiBillingDraftOutput:
        self.requires_human_review = True
        return self


class AiNarrativeOutput(BaseModel):
    narrative_text: str
    confidence: float = 0.0
    requires_review: bool = True

    @model_validator(mode="after")
    def always_require_review(self) -> AiNarrativeOutput:
        self.requires_review = True
        return self


def validate_ai_output(content: str, task_type: str = "general") -> AiOutput:
    return AiOutput(content=content, task_type=task_type)
