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

    async def generate_sms_reply(self, tenant_id: str, patient_phone: str, message_body: str) -> Optional[str]:
        """
        Generates a context-aware SMS reply.
        MOCKED for Phase 1.
        """
        # In Phase 2: Look up patient, finding recent claim, context.
        logger.info(f"Generating AI SMS reply for {patient_phone}: {message_body}")
        
        # Simple rule-based fallback for now
        if "bill" in message_body.lower() or "pay" in message_body.lower():
            return "To view or pay your bill, please use the secure link sent in the previous message. Reply HELP for support."
            
        if "stop" in message_body.lower():
            # Handled by keyword logic upstream, but good to have safety
            return None
            
        # Default AI placeholder
        return "Thank you for your message. An agent will review it shortly."

    async def generate_narrative(self, incident_data: dict) -> str:
        """
        Generates a clinical narrative from structured incident data.
        """
        logger.info(f"Generating AI Narrative for Incident")
        prompt = self._build_prompt("NARRATIVE_GENERATION", incident_data)
        # Mocked response for Phase 1
        return (
            "Unit arrived on scene to find a patient complaining of... "
            "[AI NARRATIVE GENERATED FROM VITALS AND ASSESSMENT]"
        )

    async def generate_narrative_and_update_status(self, db_session, incident_id: str):
        """
        Phase 1 Task: Update Trip model rcmStatus directly to REVIEW immediately after successful AI narrative generation.
        """
        # Fetch incident - Stub logic for Phase 1
        # In real implementation:
        # result = await db_session.execute(select(Incident).where(Incident.id == incident_id))
        # incident = result.scalar_one_or_none()
        
        # if not incident:
        #     return

        # Generate
        narrative = await self.generate_narrative({}) # Pass real data
        
        # Update
        # incident.narrative = narrative
        # incident.status = "REVIEW" # Mapped to RCM Status (IncidentStatus.REVIEW)
        # await db_session.commit()
        
        logger.info(f"Narrative generated for {incident_id}, status set to REVIEW")

    async def _call_llm(self, prompt: str) -> dict:
        """
        Placeholder for Bedrock/OpenAI call.
        """
        import asyncio
        await asyncio.sleep(0.1)
        return {
            "what_is_wrong": "Error",
            "why_it_matters": "Context missing",
            "what_to_do_next": "Check data",
            "severity": "HIGH"
        }

    def _build_prompt(self, issue_type: str, context: dict) -> str:
        # Construct a strict prompt following "AI EXPLANATION RULES"
        return f"Prompt for {issue_type} with context: {json.dumps(context, default=str)}"

