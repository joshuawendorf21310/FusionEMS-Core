from __future__ import annotations

from abc import ABC, abstractmethod

from core_app.schemas.ai import AiBillingSuggestion


class AIProvider(ABC):
    @abstractmethod
    async def analyze_chart_for_billing(self, *, chart_summary_redacted: str, payer_name: str) -> AiBillingSuggestion:
        raise NotImplementedError


class DeterministicAIProvider(AIProvider):
    async def analyze_chart_for_billing(self, *, chart_summary_redacted: str, payer_name: str) -> AiBillingSuggestion:  # noqa: ARG002
        return AiBillingSuggestion(
            suggested_icd10=["R69"],
            suggested_modifiers=["25"],
            denial_risk_score=0.2,
            missing_fields=["times_documented"],
        )
