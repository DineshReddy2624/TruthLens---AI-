"""Claim Analysis Agent: analyzes claim type, topic, time-sensitivity, and verification criteria."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import ClaimAnalysisOutput

logger = logging.getLogger(__name__)


def analyze_claim(
    claim_text: str,
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> ClaimAnalysisOutput:
    """Analyze a single factual claim using the Claim Analysis Agent."""
    return run_agent_step(
        prompt_filename="claim_analysis.md",
        user_content=claim_text,
        schema_class=ClaimAnalysisOutput,
        db=db,
        request_id=request_id,
        agent_name="claim_analysis",
        custom_llm=custom_llm,
    )
