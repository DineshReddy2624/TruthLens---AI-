"""Unit tests for NLI (Natural Language Inference) scoring service."""

import pytest
from app.services.nli import NLIEngine, run_nli_on_evidence, NLI_CONTRADICTION, NLI_ENTAILMENT, NLI_NEUTRAL
from app.models.evidence import EvidenceRecord, RetrievedSource
from app.models.verification import VerificationRequest, ExtractedClaim, InputType, RequestStatus


def test_heuristic_nli_contradiction():
    engine = NLIEngine()
    claim = "The Great Wall of China is visible from space with the naked eye."
    passage = "It is a popular myth that the Great Wall is visible from space. In reality, it is completely invisible."
    label, scores = engine.predict(claim, passage)

    assert label == NLI_CONTRADICTION
    assert scores[NLI_CONTRADICTION] > 0.5


def test_heuristic_nli_entailment():
    engine = NLIEngine()
    claim = "Water boils at 100 degrees Celsius at standard atmospheric pressure."
    passage = "Under standard atmospheric pressure of 1 atm, pure water boils at 100 degrees Celsius."
    label, scores = engine.predict(claim, passage)

    assert label == NLI_ENTAILMENT
    assert scores[NLI_ENTAILMENT] > 0.5


def test_run_nli_on_evidence_db(db_session, test_user):
    vr = VerificationRequest(user_id=test_user.id, input_type=InputType.claim, status=RequestStatus.running)
    db_session.add(vr)
    db_session.commit()

    claim = ExtractedClaim(request_id=vr.id, claim_text="The Great Wall is visible from orbit.")
    db_session.add(claim)
    db_session.commit()

    source = RetrievedSource(claim_id=claim.id, url="https://example.com/debunk", domain="example.com")
    db_session.add(source)
    db_session.commit()

    ev = EvidenceRecord(
        claim_id=claim.id,
        source_id=source.id,
        passage="The claim is false; the wall is invisible from orbit without optics.",
        rank_score=0.95,
    )
    db_session.add(ev)
    db_session.commit()

    updated = run_nli_on_evidence(
        db=db_session,
        claim_text=claim.claim_text,
        evidence_records=[ev],
    )

    assert len(updated) == 1
    assert updated[0].nli_label == NLI_CONTRADICTION
    assert updated[0].nli_scores is not None
    assert updated[0].nli_scores[NLI_CONTRADICTION] > 0.5
