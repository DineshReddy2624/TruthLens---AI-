"""Unit tests for Fact Verification Agent, confidence formula, Contradiction, and Explanation."""

import json
import pytest
from unittest.mock import MagicMock
from app.agents.fact_verification import verify_claim, calculate_verdict_confidence
from app.agents.contradiction import detect_contradictions
from app.agents.explanation import generate_explanation
from app.schemas.verification import FactVerificationOutput, ContradictionDetectionOutput, ExplanationOutput
from app.models.verification import VerdictLabel
from app.models.evidence import EvidenceRecord


class MockLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def invoke(self, messages):
        mock_resp = MagicMock()
        mock_resp.content = self.response_text
        return mock_resp


class TestFactVerificationAndConfidence:
    def test_calculate_confidence_formula(self):
        # 2 records from 2 distinct sources agreeing on contradiction
        ev1 = EvidenceRecord(
            id=1, claim_id=1, source_id=10, passage="Myth debunked.",
            nli_label="contradiction", nli_scores={"contradiction": 0.90, "entailment": 0.05, "neutral": 0.05}
        )
        ev2 = EvidenceRecord(
            id=2, claim_id=1, source_id=20, passage="Physically impossible.",
            nli_label="contradiction", nli_scores={"contradiction": 0.86, "entailment": 0.04, "neutral": 0.10}
        )

        source_evals = {10: 7.5, 20: 6.5}  # avg 7.0/8.0 = 0.875
        conf = calculate_verdict_confidence(
            verdict_label=VerdictLabel.contradicted.value,
            evidence_records=[ev1, ev2],
            source_evaluations=source_evals,
        )

        # Confidence = 0.45 * avg_nli(0.88) + 0.30 * (2/3) + 0.25 * (7.0/8.0)
        # = 0.396 + 0.20 + 0.21875 = ~0.8148
        assert 0.75 <= conf <= 0.90

    def test_insufficient_evidence_confidence(self):
        conf = calculate_verdict_confidence(
            verdict_label=VerdictLabel.insufficient_evidence.value,
            evidence_records=[],
            source_evaluations={},
        )
        assert conf == 0.20

    def test_verify_claim_agent(self, db_session):
        ev1 = EvidenceRecord(
            id=1, claim_id=1, source_id=10, passage="NASA confirms the wall cannot be seen with the naked eye.",
            nli_label="contradiction", nli_scores={"contradiction": 0.92, "entailment": 0.02, "neutral": 0.06}
        )
        source_evals = {10: 8.0}

        llm_json = json.dumps({
            "label": "Contradicted",
            "key_passage_ids": [1],
            "missing_context": "Can only be seen with optical magnification from orbit.",
            "reasoning": "Scientific consensus refutes naked eye visibility."
        })
        mock_llm = MockLLM(llm_json)

        output, conf = verify_claim(
            claim_text="The Great Wall of China is visible from space with the naked eye.",
            analysis_summary="Scientific claim about human visual acuity from LEO.",
            evidence_records=[ev1],
            source_evaluations=source_evals,
            db=db_session,
            request_id=1,
            custom_llm=mock_llm,
        )

        assert isinstance(output, FactVerificationOutput)
        assert output.label == VerdictLabel.contradicted.value
        assert output.key_passage_ids == [1]
        assert conf > 0.40


class TestContradictionAgent:
    def test_detect_contradictions_found(self, db_session):
        ev1 = EvidenceRecord(id=1, claim_id=1, source_id=1, passage="The Ming wall measures 8,850 km.")
        ev2 = EvidenceRecord(id=2, claim_id=1, source_id=2, passage="All dynasties combined measure 21,196 km.")

        llm_json = json.dumps({
            "has_conflicts": True,
            "conflicts": [
                {
                    "type": "Methodology Difference",
                    "source_a": "Ming survey",
                    "value_a": "8,850 km",
                    "source_b": "Total survey",
                    "value_b": "21,196 km",
                    "explanation": "One survey measures only Ming dynasty, the other includes all historical dynasties."
                }
            ],
            "conflict_explanation": "Discrepancy is due to which historical eras are included."
        })
        mock_llm = MockLLM(llm_json)

        res = detect_contradictions(
            claim_text="The Great Wall of China is 13,000 miles long.",
            evidence_records=[ev1, ev2],
            db=db_session,
            request_id=1,
            custom_llm=mock_llm,
        )

        assert isinstance(res, ContradictionDetectionOutput)
        assert res.has_conflicts is True
        assert len(res.conflicts) == 1


class TestExplanationAgent:
    def test_generate_explanation_citations(self, db_session):
        ev1 = EvidenceRecord(id=1, claim_id=1, source_id=1, passage="Astronauts confirm the wall is invisible to the naked eye.")
        ev2 = EvidenceRecord(id=2, claim_id=1, source_id=2, passage="Optical physics proves the resolution is insufficient.")

        llm_json = json.dumps({
            "explanation": "Astronaut observations confirm the wall is invisible to the unaided human eye [1]. Optical physics demonstrates that the human eye cannot resolve a structure only a few meters wide from low Earth orbit [2]. Popular claims of visibility originated from folklore predating human spaceflight [1].",
            "citations_used": [1, 2]
        })
        mock_llm = MockLLM(llm_json)

        res = generate_explanation(
            claim_text="The Great Wall is visible from space with the naked eye.",
            label="Contradicted",
            confidence=0.85,
            evidence_records=[ev1, ev2],
            missing_context="Can only be photographed with telephoto lenses.",
            conflict_summary=None,
            db=db_session,
            request_id=1,
            custom_llm=mock_llm,
        )

        assert isinstance(res, ExplanationOutput)
        assert "[1]" in res.explanation
        assert "[2]" in res.explanation
        assert res.citations_used == [1, 2]
