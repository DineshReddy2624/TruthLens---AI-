"""Explanation Agent: generates a 3-5 sentence plain-English summary with bracketed citations."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import ExplanationOutput
from app.models.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


def generate_explanation(
    claim_text: str,
    label: str,
    confidence: float,
    evidence_records: list[EvidenceRecord],
    missing_context: str | None = None,
    conflict_summary: str | None = None,
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> ExplanationOutput:
    """Generate 3-5 sentence plain-English explanation with [1][2] citations from evidence."""
    # Map each passage to a sequential 1-indexed citation number
    passages_with_numbers = "\n\n".join(
        f"[{idx + 1}] \"{ev.passage}\""
        for idx, ev in enumerate(evidence_records)
    ) if evidence_records else "No evidence passages provided."

    user_content = (
        f"Claim: {claim_text}\n"
        f"Verdict Label: {label}\n"
        f"Confidence Score: {confidence:.2f}\n"
        f"Key Evidence Passages:\n{passages_with_numbers}\n"
        f"Missing Context: {missing_context or 'None'}\n"
        f"Conflicts: {conflict_summary or 'None'}"
    )

    return run_agent_step(
        prompt_filename="explanation.md",
        user_content=user_content,
        schema_class=ExplanationOutput,
        db=db,
        request_id=request_id,
        agent_name="explanation_agent",
        custom_llm=custom_llm,
    )
