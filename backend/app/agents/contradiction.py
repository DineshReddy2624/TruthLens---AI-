"""Contradiction Detection Agent: detects differing numbers/dates, outdated figures, and explains disagreements."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import ContradictionDetectionOutput
from app.models.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


def detect_contradictions(
    claim_text: str,
    evidence_records: list[EvidenceRecord],
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> ContradictionDetectionOutput:
    """Identify conflicting data, differing numbers, or outdated figures among passages."""
    if not evidence_records:
        return ContradictionDetectionOutput(has_conflicts=False, conflicts=[])

    passages_text = "\n\n".join(
        f"Passage [{ev.id}] from Source {ev.source_id}:\n\"{ev.passage}\""
        for ev in evidence_records
    )

    user_content = (
        f"Claim: {claim_text}\n"
        f"Passages:\n{passages_text}"
    )

    return run_agent_step(
        prompt_filename="contradiction_detection.md",
        user_content=user_content,
        schema_class=ContradictionDetectionOutput,
        db=db,
        request_id=request_id,
        agent_name="contradiction_detection",
        custom_llm=custom_llm,
    )
