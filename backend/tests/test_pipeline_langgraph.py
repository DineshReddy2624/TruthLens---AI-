"""End-to-end integration tests for the full LangGraph verification pipeline."""

import json
import pytest
from unittest.mock import MagicMock
from app.agents.pipeline import run_verification_pipeline
from app.services.search.mock import MockSearchClient
from app.services.search.base import SearchResult
from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    InputType,
    RequestStatus,
    SearchQuery,
)
from app.models.evidence import RetrievedSource, EvidenceRecord, SourceEvaluation


class MockPipelineLLM:
    """Mock LLM responding to sequential agent requests in the LangGraph pipeline."""

    def invoke(self, messages):
        system_content = messages[0].content
        mock_resp = MagicMock()

        if "Claim Extraction Agent" in system_content:
            mock_resp.content = json.dumps({
                "claims": [
                    {
                        "claim_text": "The Great Wall of China is visible from space with the naked eye.",
                        "entities": [
                            {"name": "Great Wall of China", "category": "location"},
                            {"name": "space", "category": "location"}
                        ]
                    }
                ]
            })
        elif "Claim Analysis Agent" in system_content:
            mock_resp.content = json.dumps({
                "claim_type": "scientific",
                "topic": "Space & Optics",
                "is_time_sensitive": False,
                "time_context": None,
                "support_criteria": "Observational evidence of naked-eye visibility from orbit.",
                "contradict_criteria": "Optical calculations or astronaut reports showing invisibility.",
                "is_checkable": True,
                "uncheckable_reason": None
            })
        elif "Research Agent" in system_content:
            mock_resp.content = json.dumps({
                "queries": [
                    {"query_text": "Great Wall of China visible orbit NASA", "intent": "support"},
                    {"query_text": "Great Wall space observation study", "intent": "support"},
                    {"query_text": "Great Wall visible from space myth debunked", "intent": "contradict"},
                    {"query_text": "human eye optical resolution orbit Great Wall", "intent": "contradict"}
                ]
            })
        elif "Source Evaluation Agent" in system_content:
            mock_resp.content = json.dumps({
                "publisher_score": 2.0,
                "date_score": 1.5,
                "quality_score": 2.0,
                "corroboration_score": 2.0,
                "total_score": 7.5,
                "reason": "Authoritative scientific publishing organization with verified methodology."
            })
        elif "Fact Verification Agent" in system_content:
            mock_resp.content = json.dumps({
                "label": "Contradicted",
                "key_passage_ids": [1, 2],
                "missing_context": "Requires high-powered optics or telephoto photography to view from orbit.",
                "reasoning": "NASA and scientific optics confirm that the human eye cannot resolve the Great Wall from LEO."
            })
        elif "Contradiction Detection Agent" in system_content:
            mock_resp.content = json.dumps({
                "has_conflicts": False,
                "conflicts": [],
                "conflict_explanation": "All credible scientific sources agree that naked-eye visibility is an urban legend."
            })
        elif "Explanation Agent" in system_content:
            mock_resp.content = json.dumps({
                "explanation": "The claim that the Great Wall of China is visible from space with the naked eye is contradicted by astronaut observations and optical physics [1]. While cameras equipped with telephoto lenses can photograph sections of the wall, its narrow width renders it invisible to the unaided human eye from low Earth orbit [2]. The widespread belief is a popular myth that originated long before space exploration [1].",
                "citations_used": [1, 2]
            })
        else:
            mock_resp.content = "{}"

        return mock_resp


def test_full_pipeline_end_to_end(db_session, test_user):
    """Test full LangGraph execution from input text to final VerificationResult in MySQL."""
    # 1. Setup DB VerificationRequest
    raw_input = "People say that the Great Wall of China is visible from space with the naked eye."
    vr = VerificationRequest(
        user_id=test_user.id,
        input_type=InputType.claim,
        raw_text=raw_input,
        status=RequestStatus.pending,
    )
    db_session.add(vr)
    db_session.commit()
    db_session.refresh(vr)

    # 2. Mock Search Client with 2 authoritative sources
    mock_search_results = [
        SearchResult(
            url="https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
            title="China's Wall Less Great in View from Space - NASA",
            snippet="NASA astronauts confirm that the Great Wall is practically invisible from low Earth orbit without magnification.",
            domain="nasa.gov",
            published_date="2005-05-09",
        ),
        SearchResult(
            url="https://www.scientificamerican.com/article/is-chinas-great-wall-visible-from-space/",
            title="Is China's Great Wall Really Visible from Space? - Scientific American",
            snippet="Optical physics proves that the human eye's angular resolution cannot resolve a structure only a few meters wide from low Earth orbit.",
            domain="scientificamerican.com",
            published_date="2008-02-21",
        ),
    ]
    mock_search = MockSearchClient(predefined_results=mock_search_results)
    mock_llm = MockPipelineLLM()

    # 3. Execute LangGraph Pipeline
    final_state = run_verification_pipeline(
        request_id=vr.id,
        raw_text=raw_input,
        input_type="claim",
        custom_llm=mock_llm,
        custom_search_client=mock_search,
    )

    # 4. Verify Pipeline Final State
    assert len(final_state["claims"]) == 1
    c_id = final_state["claims"][0]["id"]

    assert c_id in final_state["analyses"]
    assert final_state["analyses"][c_id]["claim_type"] == "scientific"

    assert c_id in final_state["queries"]
    assert len(final_state["queries"][c_id]) == 4

    assert c_id in final_state["verdicts"]
    assert final_state["verdicts"][c_id]["label"] == VerdictLabel.contradicted.value
    assert final_state["verdicts"][c_id]["confidence"] > 0.5

    assert c_id in final_state["explanations"]
    assert "[1]" in final_state["explanations"][c_id]["explanation"]

    # 5. Verify Persistent MySQL Records
    # VerificationRequest status
    db_session.expire_all()
    db_vr = db_session.query(VerificationRequest).filter_by(id=vr.id).first()
    assert db_vr.status == RequestStatus.done

    # ExtractedClaim
    db_claim = db_session.query(ExtractedClaim).filter_by(id=c_id).first()
    assert db_claim is not None
    assert db_claim.claim_type == "scientific"

    # Search queries
    db_queries = db_session.query(SearchQuery).filter_by(claim_id=c_id).all()
    assert len(db_queries) == 4

    # Retrieved sources
    db_sources = db_session.query(RetrievedSource).filter_by(claim_id=c_id).all()
    assert len(db_sources) >= 2

    # Evidence records with NLI labels
    db_evidence = db_session.query(EvidenceRecord).filter_by(claim_id=c_id).all()
    assert len(db_evidence) > 0
    assert any(ev.nli_label == "contradiction" for ev in db_evidence)

    # Source evaluations
    db_evals = db_session.query(SourceEvaluation).all()
    assert len(db_evals) >= 1
    assert db_evals[0].total_score > 5.0

    # VerificationResult
    db_result = db_session.query(VerificationResult).filter_by(claim_id=c_id).first()
    assert db_result is not None
    assert db_result.label == VerdictLabel.contradicted
    assert db_result.confidence > 0.5
    assert db_result.explanation is not None
    assert "[1]" in db_result.explanation
