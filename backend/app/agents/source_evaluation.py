"""Source Evaluation Agent: scores source credibility across 4 dimensions (0-8 total)."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import SourceEvaluationOutput
from app.models.evidence import RetrievedSource, SourceEvaluation

logger = logging.getLogger(__name__)


def evaluate_source(
    claim_text: str,
    source: RetrievedSource,
    sample_content: str,
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> SourceEvaluationOutput:
    """Evaluate publisher, date, quality, and corroboration for a retrieved source."""
    user_content = (
        f"Claim: {claim_text}\n"
        f"Source URL: {source.url}\n"
        f"Domain: {source.domain or 'unknown'}\n"
        f"Title: {source.title or 'unknown'}\n"
        f"Published Date: {source.published_at.isoformat() if source.published_at else 'undated'}\n"
        f"Sample Content: {sample_content[:1500]}"
    )

    output = run_agent_step(
        prompt_filename="source_evaluation.md",
        user_content=user_content,
        schema_class=SourceEvaluationOutput,
        db=db,
        request_id=request_id,
        agent_name="source_evaluation",
        custom_llm=custom_llm,
    )

    # Persist evaluation to database if db session provided
    if db is not None:
        existing = db.query(SourceEvaluation).filter_by(source_id=source.id).first()
        if existing:
            existing.publisher_score = output.publisher_score
            existing.date_score = output.date_score
            existing.quality_score = output.quality_score
            existing.corroboration_score = output.corroboration_score
            existing.total_score = output.total_score
            existing.reason = output.reason
            db.add(existing)
        else:
            evaluation_record = SourceEvaluation(
                source_id=source.id,
                publisher_score=output.publisher_score,
                date_score=output.date_score,
                quality_score=output.quality_score,
                corroboration_score=output.corroboration_score,
                total_score=output.total_score,
                reason=output.reason,
            )
            db.add(evaluation_record)
        db.commit()

    return output
