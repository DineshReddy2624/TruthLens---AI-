"""Unit tests for Research Agent with mocked LLM."""

import json
import pytest
from unittest.mock import MagicMock
from app.agents.research import generate_search_queries
from app.schemas.verification import ResearchAgentOutput, ClaimAnalysisOutput
from app.models.logs import AgentExecutionLog


class MockLLM:
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


class TestResearchAgent:
    def test_generate_queries_balanced_intents(self, db_session):
        llm_json = json.dumps({
            "queries": [
                {"query_text": "Great Wall of China length official survey study", "intent": "support"},
                {"query_text": "State Administration of Cultural Heritage Great Wall measurements", "intent": "support"},
                {"query_text": "Great Wall of China length false overestimation debunked", "intent": "contradict"},
                {"query_text": "archaeological criticism Great Wall total distance", "intent": "contradict"},
            ]
        })
        mock_llm = MockLLM([llm_json])

        analysis = ClaimAnalysisOutput(
            claim_type="historical",
            topic="Chinese History",
            is_time_sensitive=False,
            time_context=None,
            support_criteria="Official archaeological measurements",
            contradict_criteria="Conflicting measurements",
            is_checkable=True,
            uncheckable_reason=None,
        )

        result = generate_search_queries(
            claim_text="The Great Wall of China is over 13,000 miles long.",
            analysis=analysis,
            db=db_session,
            request_id=10,
            custom_llm=mock_llm,
        )

        assert isinstance(result, ResearchAgentOutput)
        assert len(result.queries) == 4

        supports = [q for q in result.queries if q.intent == "support"]
        contradicts = [q for q in result.queries if q.intent == "contradict"]
        assert len(supports) == 2
        assert len(contradicts) == 2

        # Verify DB logging
        log = db_session.query(AgentExecutionLog).filter_by(agent_name="research_agent").first()
        assert log is not None
        assert log.request_id == 10

    def test_auto_balances_missing_intents(self, db_session):
        # LLM erroneously returned 4 support queries only
        llm_json = json.dumps({
            "queries": [
                {"query_text": "query 1", "intent": "support"},
                {"query_text": "query 2", "intent": "support"},
                {"query_text": "query 3", "intent": "support"},
                {"query_text": "query 4", "intent": "support"},
            ]
        })
        mock_llm = MockLLM([llm_json])

        result = generate_search_queries(
            claim_text="Solar energy capacity increased in 2023.",
            analysis={"is_time_sensitive": True, "time_context": "2023"},
            db=db_session,
            request_id=11,
            custom_llm=mock_llm,
        )

        contradicts = [q for q in result.queries if q.intent == "contradict"]
        assert len(contradicts) >= 1
