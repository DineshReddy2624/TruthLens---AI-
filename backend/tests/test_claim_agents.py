"""Unit tests for Claim Extraction and Claim Analysis agents with mocked LLMs."""

import json
import pytest
from unittest.mock import MagicMock
from app.agents.claim_extraction import extract_claims
from app.agents.claim_analysis import analyze_claim
from app.agents.base import run_agent_step, AgentError
from app.schemas.verification import ClaimExtractionOutput, ClaimAnalysisOutput
from app.models.logs import AgentExecutionLog


class MockLLM:
    """Mock LangChain LLM that returns pre-set content."""

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    def invoke(self, messages):
        idx = min(self.call_count, len(self.responses) - 1)
        resp_text = self.responses[idx]
        self.call_count += 1
        mock_resp = MagicMock()
        mock_resp.content = resp_text
        return mock_resp


class TestClaimExtractionAgent:
    def test_extract_claims_success(self, db_session):
        llm_json = json.dumps({
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
        mock_llm = MockLLM([llm_json])

        result = extract_claims(
            text="People often say the Great Wall of China is visible from space with the naked eye.",
            db=db_session,
            request_id=1,
            custom_llm=mock_llm,
        )

        assert isinstance(result, ClaimExtractionOutput)
        assert len(result.claims) == 1
        assert "Great Wall of China" in result.claims[0].claim_text
        assert len(result.claims[0].entities) >= 2

        # Verify DB execution log was created
        log = db_session.query(AgentExecutionLog).filter_by(agent_name="claim_extraction").first()
        assert log is not None
        assert log.request_id == 1
        assert log.output is not None

    def test_extract_claims_empty_text(self, db_session):
        result = extract_claims(text="   ", db=db_session, request_id=1)
        assert len(result.claims) == 0

    def test_retry_on_invalid_json(self, db_session):
        invalid_first = "This is not valid json at all!"
        valid_second = json.dumps({
            "claims": [
                {
                    "claim_text": "France won the FIFA World Cup in 2018.",
                    "entities": [
                        {"name": "France", "category": "organization"},
                        {"name": "FIFA World Cup", "category": "other"},
                        {"name": "2018", "category": "date"}
                    ]
                }
            ]
        })
        mock_llm = MockLLM([invalid_first, valid_second])

        result = extract_claims(
            text="France won the 2018 World Cup.",
            db=db_session,
            request_id=2,
            custom_llm=mock_llm,
        )

        assert len(result.claims) == 1
        assert mock_llm.call_count == 2


class TestClaimAnalysisAgent:
    def test_analyze_claim_success(self, db_session):
        llm_json = json.dumps({
            "claim_type": "scientific",
            "topic": "Astronomy / Space Science",
            "is_time_sensitive": False,
            "time_context": None,
            "support_criteria": "Astronaut observations or optical physics confirming human eye resolution from LEO.",
            "contradict_criteria": "NASA optical studies showing the wall width is below the angular resolution of the human eye.",
            "is_checkable": True,
            "uncheckable_reason": None
        })
        mock_llm = MockLLM([llm_json])

        result = analyze_claim(
            claim_text="The Great Wall of China is visible from low Earth orbit without magnification.",
            db=db_session,
            request_id=1,
            custom_llm=mock_llm,
        )

        assert isinstance(result, ClaimAnalysisOutput)
        assert result.claim_type == "scientific"
        assert result.is_time_sensitive is False
        assert result.is_checkable is True
        assert "Astronaut" in result.support_criteria

        # Verify DB logging
        log = db_session.query(AgentExecutionLog).filter_by(agent_name="claim_analysis").first()
        assert log is not None
        assert log.request_id == 1

    def test_uncheckable_opinion_claim(self, db_session):
        llm_json = json.dumps({
            "claim_type": "other",
            "topic": "Art / Philosophy",
            "is_time_sensitive": False,
            "time_context": None,
            "support_criteria": "Subjective consensus",
            "contradict_criteria": "Differing aesthetic opinions",
            "is_checkable": False,
            "uncheckable_reason": "Subjective value judgment with no empirical truth conditions."
        })
        mock_llm = MockLLM([llm_json])

        result = analyze_claim(
            claim_text="The Mona Lisa is the most beautiful painting ever created.",
            db=db_session,
            request_id=3,
            custom_llm=mock_llm,
        )

        assert result.is_checkable is False
        assert result.uncheckable_reason is not None
