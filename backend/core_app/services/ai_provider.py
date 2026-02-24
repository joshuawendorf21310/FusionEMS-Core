from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    async def analyze_chart_for_billing(self, *, redacted_input: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def suggest_icd10(self, *, redacted_input: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def suggest_modifiers(self, *, redacted_input: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def score_denial_risk(self, *, redacted_input: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def draft_appeal(self, *, redacted_input: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def summarize_transcript(self, *, redacted_input: str) -> dict:
        raise NotImplementedError


class DeterministicAIProvider(AIProvider):
    async def analyze_chart_for_billing(self, *, redacted_input: str) -> dict:
        return {"codes": ["A00.0"], "modifiers": ["25"], "missing_fields": [], "input_preview": redacted_input[:120]}

    async def suggest_icd10(self, *, redacted_input: str) -> dict:
        return {"codes": ["A00.0"], "input_preview": redacted_input[:120]}

    async def suggest_modifiers(self, *, redacted_input: str) -> dict:
        return {"modifiers": ["25"], "input_preview": redacted_input[:120]}

    async def score_denial_risk(self, *, redacted_input: str) -> dict:
        return {"risk": 0.2, "reasons": ["missing_documentation"], "input_preview": redacted_input[:120]}

    async def draft_appeal(self, *, redacted_input: str) -> dict:
        return {"appeal_outline": ["opening", "clinical rationale"], "input_preview": redacted_input[:120]}

    async def summarize_transcript(self, *, redacted_input: str) -> dict:
        return {"summary_points": ["dispatch", "assessment", "transport"], "input_preview": redacted_input[:120]}
