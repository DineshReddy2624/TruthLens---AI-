"""Unit tests for hybrid retrieval, passage chunking, reranking, and evidence persistence."""

import pytest
from app.services.retrieval import (
    chunk_text,
    tokenize,
    retrieve_and_store_evidence,
    HybridRetrievalEngine,
    MAX_PASSAGES_PER_CLAIM,
)
from app.services.search.mock import MockSearchClient
from app.services.search.base import SearchResult
from app.models.verification import VerificationRequest, ExtractedClaim, InputType, RequestStatus, SearchQuery
from app.models.evidence import RetrievedSource, EvidenceRecord


class TestChunkingAndTokenization:
    def test_tokenize_extracts_clean_words(self):
        tokens = tokenize("The Great Wall of China is 13,000 miles long!")
        assert "great" in tokens
        assert "wall" in tokens
        assert "china" in tokens
        assert "13" in tokens or "13000" in tokens

    def test_chunk_text_respects_size_and_paragraphs(self):
        text = (
            "Paragraph one gives historical context about ancient fortifications in northern China.\n\n"
            "Paragraph two discusses the Ming dynasty architectural enhancements and watchtowers.\n\n"
            "Paragraph three references satellite imagery and modern GPS mapping studies."
        )
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) >= 50

    def test_chunk_empty_text(self):
        assert chunk_text("") == []


class TestHybridRetrievalAndStorage:
    def test_retrieve_and_store_evidence_end_to_end(self, db_session, test_user):
        # 1. Create a verification request & claim in DB
        vr = VerificationRequest(
            user_id=test_user.id,
            input_type=InputType.claim,
            raw_text="The Great Wall of China is visible from space with the naked eye.",
            status=RequestStatus.running,
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

        # 2. Mock search client with high quality passages
        mock_results = [
            SearchResult(
                url="https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
                title="NASA - China's Wall Less Great in View from Space",
                snippet=(
                    "NASA astronauts and ISS photography confirm that the Great Wall of China "
                    "is practically invisible from low Earth orbit without binoculars or telephoto lenses. "
                    "Its materials blend in with the surrounding terrain."
                ),
                domain="nasa.gov",
                published_date="2005-05-09",
            ),
            SearchResult(
                url="https://www.scientificamerican.com/article/is-chinas-great-wall-visible-from-space/",
                title="Is China's Great Wall Really Visible from Space? - Scientific American",
                snippet=(
                    "Optical physics proves that the human eye's angular resolution cannot resolve "
                    "a structure only a few meters wide from low Earth orbit. The claim that it can be seen "
                    "with the naked eye is a persistent urban legend."
                ),
                domain="scientificamerican.com",
                published_date="2008-02-21",
            ),
        ]
        mock_search = MockSearchClient(predefined_results=mock_results)

        queries = [
            {"query_text": "Great Wall of China visible from orbit NASA", "intent": "support"},
            {"query_text": "Great Wall of China space myth debunked optical physics", "intent": "contradict"},
        ]

        # 3. Execute retrieval and storage
        passages = retrieve_and_store_evidence(
            db=db_session,
            claim_id=claim.id,
            claim_text=claim.claim_text,
            search_queries=queries,
            custom_search_client=mock_search,
        )

        # 4. Verify returned passages
        assert len(passages) > 0
        assert len(passages) <= MAX_PASSAGES_PER_CLAIM
        for p in passages:
            assert p.rank_score >= 0.0
            assert p.passage is not None
            assert len(p.passage) > 0
            assert p.url is not None
            assert p.domain is not None

        # 5. Verify database records
        # Search queries
        stored_queries = db_session.query(SearchQuery).filter_by(claim_id=claim.id).all()
        assert len(stored_queries) == 2

        # Retrieved sources
        stored_sources = db_session.query(RetrievedSource).filter_by(claim_id=claim.id).all()
        assert len(stored_sources) >= 1
        assert any("nasa.gov" in s.domain for s in stored_sources)

        # Evidence records
        stored_evidence = db_session.query(EvidenceRecord).filter_by(claim_id=claim.id).all()
        assert len(stored_evidence) == len(passages)
        for ev in stored_evidence:
            assert ev.passage is not None
            assert ev.rank_score is not None
            assert ev.source_id is not None
