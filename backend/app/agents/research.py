"""Research Agent: generates 4 targeted search queries per claim (2 support, 2 contradict)."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import ResearchAgentOutput, ClaimAnalysisOutput, GeneratedQueryItem

logger = logging.getLogger(__name__)


def generate_search_queries(
    claim_text: str,
    analysis: dict | ClaimAnalysisOutput | None = None,
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> ResearchAgentOutput:
    """Generate 4 queries per claim (2 support-seeking, 2 contradict-seeking)."""
    if isinstance(analysis, dict):
        claim_type = analysis.get("claim_type", "other")
        topic = analysis.get("topic", "General")
        is_time_sensitive = analysis.get("is_time_sensitive", False)
        time_context = analysis.get("time_context", None)
        support_criteria = analysis.get("support_criteria", "Factual records")
        contradict_criteria = analysis.get("contradict_criteria", "Debunking evidence")
    elif isinstance(analysis, ClaimAnalysisOutput):
        claim_type = analysis.claim_type
        topic = analysis.topic
        is_time_sensitive = analysis.is_time_sensitive
        time_context = analysis.time_context
        support_criteria = analysis.support_criteria
        contradict_criteria = analysis.contradict_criteria
    else:
        claim_type = "other"
        topic = "General"
        is_time_sensitive = False
        time_context = None
        support_criteria = "Factual records"
        contradict_criteria = "Debunking evidence"

    user_content = (
        f"Claim: {claim_text}\n"
        f"Type: {claim_type}\n"
        f"Topic: {topic}\n"
        f"Time-sensitive: {is_time_sensitive}\n"
        f"Time context: {time_context or 'N/A'}\n"
        f"Support criteria: {support_criteria}\n"
        f"Contradict criteria: {contradict_criteria}"
    )

    output = run_agent_step(
        prompt_filename="research_agent.md",
        user_content=user_content,
        schema_class=ResearchAgentOutput,
        db=db,
        request_id=request_id,
        agent_name="research_agent",
        custom_llm=custom_llm,
    )

    # Normalize intent labels and ensure at least 2 support & 2 contradict
    supports = [q for q in output.queries if q.intent.lower().startswith("supp")]
    contradicts = [q for q in output.queries if q.intent.lower().startswith("contra")]

    # If the LLM returned all of one intent, balance them
    if not contradicts:
        output.queries.append(
            GeneratedQueryItem(
                query_text=f"{claim_text} false debunked criticism",
                intent="contradict",
            )
        )
    if not supports:
        output.queries.append(
            GeneratedQueryItem(
                query_text=f"{claim_text} official report data study",
                intent="support",
            )
        )

    return output
