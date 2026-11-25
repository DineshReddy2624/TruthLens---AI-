"""Unit tests for Source Evaluation Agent."""

import json
import pytest
from unittest.mock import MagicMock
from app.agents.source_evaluation import evaluate_source
from app.schemas.verification import SourceEvaluationOutput
from app.models.evidence import RetrievedSource, SourceEvaluation
from app.models.verification import VerificationRequest, ExtractedClaim, InputType, RequestStatus


class MockLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def invoke(self, messages):
        mock_resp = MagicMock()
        mock_resp.content = self.response_text
        return mock_resp


def test_evaluate_source_success(db_session, test_user):
    vr = VerificationRequest(user_id=test_user.id, input_type=InputType.claim, status=RequestStatus.running)
    db_session.add(vr)
    db_session.commit()

    claim = ExtractedClaim(request_id=vr.id, claim_text="The Great Wall is visible from space.")
    db_session.add(claim)
    db_session.commit()

    source = RetrievedSource(
        claim_id=claim.id,
        url="https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
        domain="nasa.gov",
        title="China's Wall Less Great in View from Space",
    )
    db_session.add(source)
    db_session.commit()

    llm_json = json.dumps({
        "publisher_score": 2.0,
        "date_score": 1.5,
        "quality_score": 2.0,
        "corroboration_score": 2.0,
        "total_score": 7.5,
        "reason": "Official NASA research portal with primary satellite and astronaut photography."
    })
    mock_llm = MockLLM(llm_json)

    res = evaluate_source(
        claim_text=claim.claim_text,
        source=source,
        sample_content="NASA astronauts confirm the wall is not visible without magnification.",
        db=db_session,
        request_id=vr.id,
        custom_llm=mock_llm,
    )

    assert isinstance(res, SourceEvaluationOutput)
    assert res.publisher_score == 2.0
    assert res.total_score == 7.5
    assert "NASA" in res.reason

    # Verify DB record
    eval_db = db_session.query(SourceEvaluation).filter_by(source_id=source.id).first()
    assert eval_db is not None
    assert eval_db.total_score == 7.5
    assert eval_db.publisher_score == 2.0
