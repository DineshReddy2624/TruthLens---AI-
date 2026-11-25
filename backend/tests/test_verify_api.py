"""API tests for verification submission endpoints (/api/v1/verify)."""

import json
from unittest.mock import patch
import pytest
from app.schemas.verification import ClaimExtractionOutput, ClaimAnalysisOutput, ExtractedClaimItem, ExtractedEntity


@pytest.fixture
def mock_pipeline():
    """Mock the LangGraph pipeline for API endpoint testing."""
    from tests.conftest import TestingSessionLocal
    from app.models.verification import VerificationRequest, ExtractedClaim, VerificationResult, VerdictLabel, RequestStatus
    from app.models.evidence import RetrievedSource, EvidenceRecord

    def fake_pipeline(request_id, raw_text, input_type="claim", **kwargs):
        db = TestingSessionLocal()
        try:
            claim = ExtractedClaim(
                request_id=request_id,
                claim_text="The Great Wall of China is over 13,000 miles long.",
                claim_type="historical",
                entities=[{"name": "Great Wall of China", "category": "location"}],
                analysis={
                    "claim_type": "historical",
                    "topic": "Chinese History and Architecture",
                    "is_checkable": True,
                },
            )
            db.add(claim)
            db.commit()
            db.refresh(claim)

            source = RetrievedSource(
                claim_id=claim.id,
                url="https://example.com/great-wall",
                domain="example.com",
                title="Great Wall Survey",
            )
            db.add(source)
            db.commit()
            db.refresh(source)

            ev = EvidenceRecord(
                claim_id=claim.id,
                source_id=source.id,
                passage="The Ming wall measures 8,850 km while all dynasties combined measure 21,196 km.",
                nli_label="entailment",
                rank_score=0.92,
            )
            db.add(ev)
            db.commit()
            db.refresh(ev)

            res = VerificationResult(
                claim_id=claim.id,
                label=VerdictLabel.supported,
                confidence=0.88,
                key_passage_ids=[ev.id],
                explanation="Archaeological surveys confirm the length exceeds 13,000 miles [1].",
            )
            db.add(res)

            vr = db.query(VerificationRequest).filter_by(id=request_id).first()
            if vr:
                vr.status = RequestStatus.done
                db.add(vr)

            db.commit()
        finally:
            db.close()
        return {}

    with patch("app.api.v1.verify.run_verification_pipeline", side_effect=fake_pipeline):
        yield



class TestSubmitTextAPI:
    def test_submit_text_success(self, client, auth_headers, mock_pipeline):
        response = client.post(
            "/api/v1/verify/submit-text",
            headers=auth_headers,
            json={
                "text": "The Great Wall of China is over 13,000 miles long according to official surveys.",
                "input_type": "article",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] > 0
        assert data["claims_count"] == 1
        assert data["status"] == "done"
        assert data["input_type"] == "article"

    def test_submit_text_too_short(self, client, auth_headers):
        response = client.post(
            "/api/v1/verify/submit-text",
            headers=auth_headers,
            json={"text": "Hi", "input_type": "claim"},
        )
        assert response.status_code == 422

    def test_submit_text_unauthorized(self, client):
        response = client.post(
            "/api/v1/verify/submit-text",
            json={"text": "Valid text here for testing.", "input_type": "claim"},
        )
        assert response.status_code == 403


class TestSubmitUrlAPI:
    def test_submit_url_ssrf_blocked(self, client, auth_headers):
        response = client.post(
            "/api/v1/verify/submit-url",
            headers=auth_headers,
            json={"url": "http://127.0.0.1:8000/api/v1/admin"},
        )
        assert response.status_code == 400
        assert "Security violation" in response.json()["detail"]

    def test_submit_url_success(self, client, auth_headers, mock_pipeline):
        with patch("app.api.v1.verify.extract_text_from_url", return_value=("Article about Great Wall.", "Great Wall")):
            response = client.post(
                "/api/v1/verify/submit-url",
                headers=auth_headers,
                json={"url": "https://en.wikipedia.org/wiki/Great_Wall_of_China"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["input_type"] == "url"
            assert data["claims_count"] == 1


class TestSubmitFileAPI:
    def test_submit_txt_file_success(self, client, auth_headers, mock_pipeline):
        file_content = b"The Great Wall of China is over 13,000 miles long."
        response = client.post(
            "/api/v1/verify/submit-file",
            headers=auth_headers,
            files={"file": ("test_doc.txt", file_content, "text/plain")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["input_type"] == "file"
        assert data["claims_count"] == 1

    def test_submit_disallowed_file_extension(self, client, auth_headers):
        response = client.post(
            "/api/v1/verify/submit-file",
            headers=auth_headers,
            files={"file": ("malicious.exe", b"binary content", "application/x-msdownload")},
        )
        assert response.status_code == 400
        assert "Unsupported file extension" in response.json()["detail"]


class TestGetVerificationRequestAPI:
    def test_get_and_list_requests(self, client, auth_headers, mock_pipeline):
        # First submit
        submit_res = client.post(
            "/api/v1/verify/submit-text",
            headers=auth_headers,
            json={"text": "The Great Wall is over 13,000 miles long.", "input_type": "claim"},
        )
        req_id = submit_res.json()["id"]

        # Get detail
        get_res = client.get(f"/api/v1/verify/{req_id}", headers=auth_headers)
        assert get_res.status_code == 200
        detail = get_res.json()
        assert detail["id"] == req_id
        assert len(detail["claims"]) == 1
        assert detail["claims"][0]["claim_type"] == "historical"
        assert detail["claims"][0]["analysis"]["is_checkable"] is True

        # List requests
        list_res = client.get("/api/v1/verify", headers=auth_headers)
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1
