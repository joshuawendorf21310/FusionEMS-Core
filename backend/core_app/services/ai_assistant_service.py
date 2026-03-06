import json
import logging
from typing import Optional

# import boto3
# from core_app.core.config import get_settings
from core_app.models.deployment import FailureAudit
from core_app.models.billing import ClaimIssue

logger = logging.getLogger(__name__)

class AIAssistantService:
    """
    Implements PART 9: AI FOUNDER ASSISTANT STANDARD.
    
    Generates plain-English explanations for technical failures.
    """
    def __init__(self):
        # self.bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        pass

    async def explain_deployment_failure(self, failure: FailureAudit, technical_context: dict) -> FailureAudit:
        """
        Populate FailureAudit with AI explanation.
        """
        prompt = self._build_prompt("DEPLOYMENT_FAILURE", technical_context)
        explanation = await self._call_llm(prompt)
        
        failure.what_is_wrong = explanation.get("what_is_wrong", "Unknown Error")
        failure.why_it_matters = explanation.get("why_it_matters", "Deployment halted.")
        failure.what_to_do_next = explanation.get("what_to_do_next", "Contact Support.")
        failure.severity = explanation.get("severity", "HIGH")
        
        return failure

    async def explain_claim_issue(self, issue: ClaimIssue, claim_data: dict) -> ClaimIssue:
        """
        Populate ClaimIssue with AI explanation.
        """
        prompt = self._build_prompt("CLAIM_ISSUE", claim_data)
        explanation = await self._call_llm(prompt)
        
        issue.what_is_wrong = explanation.get("what_is_wrong", "Invalid data.")
        issue.why_it_matters = explanation.get("why_it_matters", "Claim will be denied.")
        issue.what_to_do_next = explanation.get("what_to_do_next", "Correct the field.")
        
        return issue

    def _build_prompt(self, issue_type: str, context: dict) -> str:
        # Construct a strict prompt following "AI EXPLANATION RULES"
        return f"""
        You are an expert billing and deployment assistant for a non-technical paramedic founder.
        Analyze this {issue_type}: {json.dumps(context)}
        
        Return a JSON object with:
        - what_is_wrong (Plain English, no jargon without definition)
        - why_it_matters (Business impact)
        - what_to_do_next (Concrete step)
        - severity (BLOCKING, HIGH, MEDIUM, LOW)
        
        Rules:
        - Never say 'invalid field' without naming it.
        - Distinguish fact from judgment.
        """

    async def _call_llm(self, prompt: str) -> dict:
        # Mock LLM call for now
        # response = self.bedrock.invoke_model(...)
        logger.info(f"Mocking LLM call for prompt: {prompt[:50]}...")
        return {
            "what_is_wrong": "The provided subscription ID is invalid.",
            "why_it_matters": "We cannot bill the agency.",
            "what_to_do_next": "Check the Stripe Dashboard for the correct ID.",
            "severity": "BLOCKING"
        }
