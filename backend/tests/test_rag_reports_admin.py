"""Tests for RAG Assistant, History search, PDF Reports, and Admin endpoints."""

import os
from unittest.mock import patch, MagicMock
import pytest

from app.models.user import User, UserRole
from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    InputType,
    RequestStatus,
    VerificationReport,
)
from app.models.evidence import RetrievedSource, EvidenceRecord
from app.models.logs import ChatHistory, ChatRole, TrustedSource
from app.services.rag import answer_rag_question
from app.services.report import generate_pdf_report


class MockRAGLLM:
    """Mock LLM for testing RAG Assistant and Report Generation."""
    def invoke(self, messages, **kwargs):
        mock_resp = MagicMock()
        text = str(messages)
        if "report_generation" in text or "Report Generation Agent" in text or "Executive Summary" in text:
            mock_resp.content = (
                '{"executive_summary": "Test executive summary confirming Great Wall is invisible from space.", '
                '"overall_assessment": "Contradicted"}'
            )
        else:
            mock_resp.content = (
                '{"answer": "NASA astronauts confirmed the Great Wall is not visible to the naked eye [1].", '
                '"citations_used": [1], "is_sufficient": true}'
            )
        return mock_resp


@pytest.fixture
def sample_verified_request(db_session, test_user):
    """Seed a sample verified request with claims, evidence, and results."""
    vr = VerificationRequest(
        user_id=test_user.id,
        input_type=InputType.claim,
        raw_text="The Great Wall of China is visible from space with the naked eye.",
        status=RequestStatus.done,
    )
    db_session.add(vr)
    db_session.commit()
    db_session.refresh(vr)

    claim = ExtractedClaim(
        request_id=vr.id,
        claim_text="The Great Wall of China is visible from space with the naked eye.",
        claim_type="scientific",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    source = RetrievedSource(
        claim_id=claim.id,
        url="https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
        domain="nasa.gov",
        title="China's Wall Less Great in View from Space",
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    ev = EvidenceRecord(
        claim_id=claim.id,
        source_id=source.id,
        passage="NASA astronauts confirm that the Great Wall is practically invisible from low Earth orbit without magnification.",
        nli_label="contradiction",
        rank_score=0.95,
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    res = VerificationResult(
        claim_id=claim.id,
        label=VerdictLabel.contradicted,
        confidence=0.91,
        key_passage_ids=[ev.id],
        explanation="Optics and astronaut observation confirm it cannot be resolved with the naked eye [1].",
    )
    db_session.add(res)
    db_session.commit()
    db_session.refresh(res)

    return vr


class TestRAGAssistant:
    def test_rag_chat_sufficient_evidence(self, db_session, test_user, sample_verified_request):
        mock_llm = MockRAGLLM()
        res = answer_rag_question(
            db=db_session,
            request_id=sample_verified_request.id,
            user_id=test_user.id,
            user_message="Can astronauts see the Great Wall from space?",
            custom_llm=mock_llm,
        )
        assert res.is_sufficient is True
        assert "[1]" in res.answer
        assert len(res.citations_used) == 1
        assert res.citations_metadata[0]["source_url"] == "https://www.nasa.gov/vision/space/workinginspace/great_wall.html"

        # Check DB chat history
        history = db_session.query(ChatHistory).filter_by(request_id=sample_verified_request.id).all()
        assert len(history) == 2  # user and assistant
        assert history[0].role == ChatRole.user
        assert history[1].role == ChatRole.assistant

    def test_rag_chat_insufficient_evidence(self, db_session, test_user, sample_verified_request):
        # Query on unrelated topic (no BM25 overlap)
        res = answer_rag_question(
            db=db_session,
            request_id=sample_verified_request.id,
            user_id=test_user.id,
            user_message="What is the recipe for chocolate chip cookies?",
        )
        assert res.is_sufficient is False
        assert "not enough evidence" in res.answer.lower()
        assert res.citations_used == []


class TestPDFReportGeneration:
    def test_generate_pdf_report_success(self, db_session, sample_verified_request):
        mock_llm = MockRAGLLM()
        pdf_path = generate_pdf_report(db=db_session, request_id=sample_verified_request.id, custom_llm=mock_llm)
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        assert os.path.getsize(pdf_path) > 1000

        # Check DB record
        rep = db_session.query(VerificationReport).filter_by(request_id=sample_verified_request.id).first()
        assert rep is not None
        assert rep.pdf_path == pdf_path


class TestHistoryAPI:
    def test_get_history_list(self, client, auth_headers, sample_verified_request):
        response = client.get("/api/v1/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == sample_verified_request.id

    def test_get_history_filter_label(self, client, auth_headers, sample_verified_request):
        # Filter by Contradicted
        response = client.get("/api/v1/history?label=Contradicted", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Filter by Supported (should return empty)
        response_empty = client.get("/api/v1/history?label=Supported", headers=auth_headers)
        assert response_empty.status_code == 200
        assert len(response_empty.json()) == 0


class TestAdminAPI:
    def test_admin_stats(self, client, admin_headers, sample_verified_request):
        response = client.get("/api/v1/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] >= 1
        assert "Contradicted" in data["label_distribution"]

    def test_admin_trusted_sources_crud(self, client, admin_headers):
        # 1. Add trusted source
        res_add = client.post(
            "/api/v1/admin/trusted-sources",
            headers=admin_headers,
            json={"domain": "reuters.com", "category": "News", "notes": "International news agency"},
        )
        assert res_add.status_code == 201
        ts_id = res_add.json()["id"]

        # 2. List trusted sources
        res_list = client.get("/api/v1/admin/trusted-sources", headers=admin_headers)
        assert res_list.status_code == 200
        domains = [s["domain"] for s in res_list.json()]
        assert "reuters.com" in domains

        # 3. Delete trusted source
        res_del = client.delete(f"/api/v1/admin/trusted-sources/{ts_id}", headers=admin_headers)
        assert res_del.status_code == 204
