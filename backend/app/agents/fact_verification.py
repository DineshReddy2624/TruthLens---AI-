"""Fact Verification Agent: determines final verdict and calculates confidence score."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.agents.base import run_agent_step
from app.schemas.verification import FactVerificationOutput
from app.models.verification import VerdictLabel
from app.models.evidence import EvidenceRecord, SourceEvaluation

logger = logging.getLogger(__name__)

# Valid exact verdict labels
VALID_VERDICTS = {
    VerdictLabel.supported.value,
    VerdictLabel.contradicted.value,
    VerdictLabel.partially_supported.value,
    VerdictLabel.insufficient_evidence.value,
    VerdictLabel.conflicting_evidence.value,
}


def calculate_verdict_confidence(
    verdict_label: str,
    evidence_records: list[EvidenceRecord],
    source_evaluations: dict[int, float],  # source_id -> total_score (0-8)
) -> float:
    """Calculate deterministic verification confidence score in [0.0, 1.0].

    Formula:
        Confidence = 0.45 * NLI_agreement + 0.30 * Source_Count_Norm + 0.25 * Avg_Source_Score_Norm

    Components:
        - NLI_agreement: Average NLI probability of the selected direction across agreeing passages.
          If label is "Insufficient Evidence", defaults to 0.15.
        - Source_Count_Norm: min(independent_sources_count, 3) / 3.0.
        - Avg_Source_Score_Norm: average source score of agreeing sources / 8.0.
    """
    if verdict_label == VerdictLabel.insufficient_evidence.value or not evidence_records:
        return 0.20

    # Determine target NLI label corresponding to verdict
    if verdict_label == VerdictLabel.supported.value:
        target_nli = "entailment"
    elif verdict_label == VerdictLabel.contradicted.value:
        target_nli = "contradiction"
    elif verdict_label == VerdictLabel.conflicting_evidence.value:
        return 0.65  # High confidence that sources disagree
    else:
        target_nli = "entailment"

    agreeing_records = [
        ev for ev in evidence_records
        if ev.nli_label == target_nli and ev.nli_scores
    ]

    if not agreeing_records:
        # If no explicit NLI agreement found, use fallback conservative confidence
        return 0.35

    # 1. NLI agreement component (0.0 to 1.0)
    avg_nli = float(np_mean := sum(ev.nli_scores.get(target_nli, 0.5) for ev in agreeing_records) / len(agreeing_records))

    # 2. Independent sources count (normalized to 1.0 at >= 3 sources)
    unique_sources = {ev.source_id for ev in agreeing_records}
    source_count_norm = min(len(unique_sources), 3) / 3.0

    # 3. Source credibility component (normalized from 0-8 to 0.0-1.0)
    source_scores = [source_evaluations.get(s_id, 4.0) for s_id in unique_sources]
    avg_source_score = (sum(source_scores) / len(source_scores)) if source_scores else 4.0
    source_score_norm = min(max(avg_source_score / 8.0, 0.0), 1.0)

    # Weighted combination
    confidence = (0.45 * avg_nli) + (0.30 * source_count_norm) + (0.25 * source_score_norm)
    return round(float(min(max(confidence, 0.05), 0.98)), 4)


def verify_claim(
    claim_text: str,
    analysis_summary: str,
    evidence_records: list[EvidenceRecord],
    source_evaluations: dict[int, float],
    db: Session | None = None,
    request_id: int | None = None,
    custom_llm: Any = None,
) -> tuple[FactVerificationOutput, float]:
    """Verify claim with LLM using passages, NLI scores, and source credibility, and compute confidence."""
    # Build prompt input listing passages with IDs, NLI scores, and source credibility
    passage_entries = []
    for ev in evidence_records:
        nli_str = ""
        if ev.nli_scores:
            nli_str = f" [NLI: {ev.nli_label} (entail: {ev.nli_scores.get('entailment', 0):.2f}, contra: {ev.nli_scores.get('contradiction', 0):.2f})]"
        src_score = source_evaluations.get(ev.source_id, 4.0)
        passage_entries.append(
            f"Passage ID [{ev.id}] (Source Score: {src_score}/8.0){nli_str}:\n\"{ev.passage}\""
        )

    passages_text = "\n\n".join(passage_entries) if passage_entries else "No evidence passages available."

    user_content = (
        f"Claim: {claim_text}\n"
        f"Claim Analysis: {analysis_summary}\n"
        f"Retrieved Passages & NLI Scores:\n{passages_text}"
    )

    output = run_agent_step(
        prompt_filename="fact_verification.md",
        user_content=user_content,
        schema_class=FactVerificationOutput,
        db=db,
        request_id=request_id,
        agent_name="fact_verification",
        custom_llm=custom_llm,
    )

    # Enforce strict canonical label formatting
    normalized_label = None
    for valid_lbl in VALID_VERDICTS:
        if output.label.strip().lower() == valid_lbl.lower():
            normalized_label = valid_lbl
            break

    if not normalized_label:
        normalized_label = VerdictLabel.insufficient_evidence.value
    output.label = normalized_label

    # Compute deterministic confidence score
    confidence = calculate_verdict_confidence(
        verdict_label=output.label,
        evidence_records=evidence_records,
        source_evaluations=source_evaluations,
    )

    return output, confidence
