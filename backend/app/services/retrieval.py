"""Hybrid retrieval and reranking engine: BM25 + Dense embeddings (ChromaDB) + Cross-Encoder reranking."""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.evidence import RetrievedSource, EvidenceRecord
from app.models.verification import SearchQuery, QueryIntent
from app.services.extractor import extract_text_from_url, SSRFSecurityError, ExtractorError
from app.services.search.factory import get_search_client
from app.schemas.verification import RetrievedPassageItem

logger = logging.getLogger(__name__)

# Constants
MAX_PASSAGES_PER_CLAIM = 5
CHUNK_SIZE_CHARS = 1200
CHUNK_OVERLAP_CHARS = 200


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words for BM25."""
    return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Split clean text into overlapping passage chunks respecting sentence / paragraph breaks."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{p}".strip() if current_chunk else p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If paragraph itself is larger than chunk_size, split by sentences
            if len(p) > chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", p)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {s}".strip() if sub_chunk else s
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = s
                current_chunk = sub_chunk
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    # Filter out very short or empty chunks (< 50 chars)
    return [c for c in chunks if len(c) >= 50]


def get_chroma_client():
    """Get ChromaDB client: connects to remote Chroma if available, falls back to EphemeralClient."""
    import chromadb
    settings = get_settings()
    try:
        # Try connecting to HTTP Chroma service
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        client.heartbeat()
        return client
    except Exception:
        # In-memory ephemeral client for tests and standalone local runs
        return chromadb.EphemeralClient()


class HybridRetrievalEngine:
    """Orchestrates BM25 keyword search, ChromaDB dense vector search, and cross-encoder reranking."""

    def __init__(self, chroma_client=None):
        self.chroma_client = chroma_client or get_chroma_client()
        self._cross_encoder = None
        self._embedding_model = None

    def _get_cross_encoder(self):
        """Lazy-load cross-encoder model."""
        if self._cross_encoder is None:
            try:
                from sentence_transformers import CrossEncoder
                self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder model ({e}); using token overlap fallback.")
                self._cross_encoder = "fallback"
        return self._cross_encoder

    def rerank_passages(self, claim_text: str, candidate_passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score (claim_text, passage) pairs with cross-encoder or hybrid score."""
        if not candidate_passages:
            return []

        model = self._get_cross_encoder()

        if model != "fallback":
            try:
                pairs = [[claim_text, p["passage"]] for p in candidate_passages]
                scores = model.predict(pairs)
                # Normalize cross-encoder logits with sigmoid
                sigmoid_scores = 1.0 / (1.0 + np.exp(-np.array(scores)))
                for p, score in zip(candidate_passages, sigmoid_scores):
                    p["rank_score"] = float(score)
                return sorted(candidate_passages, key=lambda x: x["rank_score"], reverse=True)
            except Exception as e:
                logger.warning(f"Cross-encoder prediction failed: {e}; falling back to combined score.")

        # Fallback: combine normalized BM25 + dense score
        for p in candidate_passages:
            bm25 = p.get("bm25_score", 0.0)
            dense = p.get("dense_score", 0.0)
            p["rank_score"] = round(0.5 * bm25 + 0.5 * dense, 4)

        return sorted(candidate_passages, key=lambda x: x["rank_score"], reverse=True)


def retrieve_and_store_evidence(
    db: Session,
    claim_id: int,
    claim_text: str,
    search_queries: list[dict[str, str]],
    custom_search_client: Any = None,
    engine: HybridRetrievalEngine | None = None,
) -> list[RetrievedPassageItem]:
    """Execute search queries, fetch pages, chunk, run BM25+BGE hybrid search, rerank, and persist top 5."""
    from rank_bm25 import BM25Okapi

    search_client = custom_search_client or get_search_client()
    retrieval_engine = engine or HybridRetrievalEngine()

    # Step 1: Save queries and gather search results
    all_search_results = []
    seen_urls = set()

    for q in search_queries:
        query_text = q.get("query_text", "")
        intent_str = q.get("intent", "support").lower()
        intent = QueryIntent.contradict if "contra" in intent_str else QueryIntent.support

        # Persist SearchQuery in DB
        sq_record = SearchQuery(
            claim_id=claim_id,
            query_text=query_text,
            intent=intent,
        )
        db.add(sq_record)

        # Call Search API
        results = search_client.search(query=query_text, max_results=3)
        for res in results:
            if res.url and res.url not in seen_urls:
                seen_urls.add(res.url)
                all_search_results.append(res)

    db.commit()

    if not all_search_results:
        logger.warning(f"No search results returned for claim {claim_id}.")
        return []

    # Step 2: Fetch and chunk page contents
    all_chunks: list[dict[str, Any]] = []

    for res in all_search_results:
        # Check SSRF before fetching
        try:
            page_text, page_title = extract_text_from_url(res.url)
        except (SSRFSecurityError, ExtractorError, Exception) as e:
            logger.debug(f"Could not extract content from {res.url}: {e}; using search snippet.")
            page_text = res.snippet
            page_title = res.title

        title = page_title or res.title or "Unknown Title"
        domain = res.domain or urlparse(res.url).netloc.lower().replace("www.", "")

        chunks = chunk_text(page_text)
        if not chunks and res.snippet:
            chunks = [res.snippet]

        for chunk in chunks:
            all_chunks.append({
                "url": res.url,
                "title": title,
                "domain": domain,
                "published_date": res.published_date,
                "passage": chunk,
            })

    if not all_chunks:
        return []

    # Step 3: BM25 Scoring
    tokenized_corpus = [tokenize(c["passage"]) for c in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = tokenize(claim_text)
    bm25_raw_scores = bm25.get_scores(query_tokens)

    # Normalize BM25 scores to [0, 1]
    max_bm25 = max(bm25_raw_scores) if len(bm25_raw_scores) > 0 and max(bm25_raw_scores) > 0 else 1.0
    for chunk, raw_score in zip(all_chunks, bm25_raw_scores):
        chunk["bm25_score"] = float(raw_score / max_bm25)

    # Step 4: ChromaDB Dense Search (Vectors stay in ChromaDB, NOT MySQL)
    collection_name = f"claim_{claim_id}_{int(datetime.now(timezone.utc).timestamp())}"
    try:
        collection = retrieval_engine.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"claim_id": str(claim_id)},
        )

        # Add chunks to collection
        ids = [f"chk_{i}_{hashlib.md5(c['passage'].encode()).hexdigest()[:8]}" for i, c in enumerate(all_chunks)]
        documents = [c["passage"] for c in all_chunks]
        metadatas = [{"url": c["url"], "title": c["title"], "domain": c["domain"]} for c in all_chunks]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        # Query collection with claim text
        query_res = collection.query(query_texts=[claim_text], n_results=min(len(all_chunks), 15))

        returned_ids = query_res["ids"][0] if query_res["ids"] else []
        distances = query_res["distances"][0] if query_res.get("distances") and query_res["distances"] else []

        id_to_dense_score = {}
        for chk_id, dist in zip(returned_ids, distances):
            # Convert cosine distance to similarity in [0, 1]
            similarity = max(0.0, 1.0 - float(dist))
            id_to_dense_score[chk_id] = similarity

        for chk_id, chunk in zip(ids, all_chunks):
            chunk["dense_score"] = id_to_dense_score.get(chk_id, 0.0)

        # Clean up temporary Chroma collection
        try:
            retrieval_engine.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Chroma dense retrieval error: {e}; falling back to BM25 scores.")
        for chunk in all_chunks:
            chunk["dense_score"] = chunk.get("bm25_score", 0.0)

    # Step 5: Candidate filtering (take top 15 candidates before cross-encoder rerank)
    for c in all_chunks:
        c["hybrid_candidate_score"] = 0.5 * c.get("bm25_score", 0.0) + 0.5 * c.get("dense_score", 0.0)

    candidates = sorted(all_chunks, key=lambda x: x["hybrid_candidate_score"], reverse=True)[:15]

    # Step 6: Cross-Encoder Reranking
    reranked = retrieval_engine.rerank_passages(claim_text=claim_text, candidate_passages=candidates)

    # Deduplicate by passage content and keep top 5
    top_passages: list[dict[str, Any]] = []
    seen_texts = set()

    for p in reranked:
        norm_passage = p["passage"].strip().lower()[:100]
        if norm_passage not in seen_texts:
            seen_texts.add(norm_passage)
            top_passages.append(p)
        if len(top_passages) >= MAX_PASSAGES_PER_CLAIM:
            break

    # Step 7: Persist Sources and Evidence Records in MySQL
    # Map each unique URL to a RetrievedSource record
    url_to_source_id: dict[str, int] = {}
    for p in top_passages:
        url = p["url"]
        if url not in url_to_source_id:
            published_dt = None
            if p.get("published_date"):
                try:
                    published_dt = datetime.fromisoformat(p["published_date"].replace("Z", "+00:00"))
                except Exception:
                    pass

            source_record = RetrievedSource(
                claim_id=claim_id,
                url=url,
                domain=p["domain"],
                title=p["title"][:1024],
                publisher=p["domain"],
                published_at=published_dt,
            )
            db.add(source_record)
            db.commit()
            db.refresh(source_record)
            url_to_source_id[url] = source_record.id

    # Persist EvidenceRecord for each passage
    output_items: list[RetrievedPassageItem] = []
    for p in top_passages:
        src_id = url_to_source_id[p["url"]]
        ev_record = EvidenceRecord(
            claim_id=claim_id,
            source_id=src_id,
            passage=p["passage"],
            rank_score=p.get("rank_score", 0.0),
        )
        db.add(ev_record)
        db.commit()
        db.refresh(ev_record)

        output_items.append(
            RetrievedPassageItem(
                passage_id=ev_record.id,
                source_id=src_id,
                url=p["url"],
                title=p["title"],
                domain=p["domain"],
                passage=p["passage"],
                rank_score=p.get("rank_score", 0.0),
                bm25_score=p.get("bm25_score"),
                dense_score=p.get("dense_score"),
            )
        )

    return output_items
