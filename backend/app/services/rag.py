"""RAG Assistant service for interactive Q&A over verified articles and documents."""

import logging
from typing import Any
from sqlalchemy.orm import Session
from rank_bm25 import BM25Okapi

from pydantic import BaseModel, Field
from app.models.logs import ChatHistory, ChatRole
from app.models.verification import VerificationRequest, ExtractedClaim
from app.models.evidence import EvidenceRecord, RetrievedSource
from app.agents.base import run_agent_step
from app.services.retrieval import tokenize
from app.schemas.verification import RAGChatResponse

logger = logging.getLogger(__name__)


class RAGAgentOutput(BaseModel):
    answer: str
    citations_used: list[int] = Field(default_factory=list)
    is_sufficient: bool = True


def answer_rag_question(
    db: Session,
    request_id: int,
    user_id: int,
    user_message: str,
    custom_llm: Any = None,
) -> RAGChatResponse:
    """Answer questions strictly from verified evidence or return 'not enough evidence'."""
    # 1. Fetch claims and evidence records for this request
    claims = db.query(ExtractedClaim).filter_by(request_id=request_id).all()
    claim_ids = [c.id for c in claims]

    evidence_records: list[EvidenceRecord] = []
    if claim_ids:
        evidence_records = (
            db.query(EvidenceRecord)
            .filter(EvidenceRecord.claim_id.in_(claim_ids))
            .all()
        )

    # Record user message in chat history
    user_chat = ChatHistory(
        request_id=request_id,
        user_id=user_id,
        role=ChatRole.user,
        message=user_message,
        citations=None,
    )
    db.add(user_chat)
    db.commit()

    # If no evidence records exist at all
    if not evidence_records:
        no_ev_ans = "There is not enough evidence in the verified document to answer this question."
        asst_chat = ChatHistory(
            request_id=request_id,
            user_id=user_id,
            role=ChatRole.assistant,
            message=no_ev_ans,
            citations={"citations": [], "is_sufficient": False},
        )
        db.add(asst_chat)
        db.commit()
        return RAGChatResponse(
            answer=no_ev_ans,
            citations_used=[],
            citations_metadata=[],
            is_sufficient=False,
        )

    # 2. Score similarity using token overlap and BM25 over evidence passages
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for", "and", "or", "it", "that", "this", "on", "with", "as", "at", "by", "from", "can", "do", "does", "what", "how"}
    tokenized_corpus = [tokenize(e.passage) for e in evidence_records]
    query_tokens = tokenize(user_message)
    q_keywords = [t for t in query_tokens if t not in stopwords] or query_tokens

    scored_records = []
    if len(tokenized_corpus) > 3:
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(query_tokens)
        for ev, doc_toks, score in zip(evidence_records, tokenized_corpus, bm25_scores):
            overlap = len(set(q_keywords) & set(doc_toks))
            scored_records.append((ev, score if overlap > 0 else 0.0, overlap))
    else:
        for ev, doc_toks in zip(evidence_records, tokenized_corpus):
            overlap = len(set(q_keywords) & set(doc_toks))
            ratio = overlap / max(len(q_keywords), 1)
            scored_records.append((ev, ratio, overlap))

    # Sort by score then overlap
    scored_records.sort(key=lambda x: (x[1], x[2]), reverse=True)
    top_scored = [r[0] for r in scored_records if r[2] > 0][:5]

    # If no keyword overlap exists at all
    if not top_scored:
        no_ev_ans = "There is not enough evidence in the verified document to answer this question."
        asst_chat = ChatHistory(
            request_id=request_id,
            user_id=user_id,
            role=ChatRole.assistant,
            message=no_ev_ans,
            citations={"citations": [], "is_sufficient": False},
        )
        db.add(asst_chat)
        db.commit()
        return RAGChatResponse(
            answer=no_ev_ans,
            citations_used=[],
            citations_metadata=[],
            is_sufficient=False,
        )

    # 3. Format passages for prompt
    passages_text_list = []
    passage_id_map = {}  # index 1..k -> EvidenceRecord
    for idx, ev in enumerate(top_scored, 1):
        source = db.query(RetrievedSource).filter_by(id=ev.source_id).first()
        domain = source.domain if source else "source"
        passages_text_list.append(f"[{idx}] (Source: {domain})\n{ev.passage}")
        passage_id_map[idx] = ev

    passages_str = "\n\n".join(passages_text_list)

    # 4. Invoke LLM via run_agent_step
    user_prompt_content = f"User Question: {user_message}\n\nContext & Evidence Passages:\n{passages_str}"
    try:
        agent_out: RAGAgentOutput = run_agent_step(
            prompt_filename="rag_assistant.md",
            user_content=user_prompt_content,
            schema_class=RAGAgentOutput,
            db=db,
            request_id=request_id,
            agent_name="RAG Assistant",
            custom_llm=custom_llm,
        )

        answer = agent_out.answer
        used_citations = agent_out.citations_used
        is_sufficient = agent_out.is_sufficient

        # Build citation metadata
        citations_meta = []
        for c_idx in used_citations:
            if c_idx in passage_id_map:
                ev = passage_id_map[c_idx]
                source = db.query(RetrievedSource).filter_by(id=ev.source_id).first()
                citations_meta.append({
                    "citation_number": c_idx,
                    "evidence_id": ev.id,
                    "source_url": source.url if source else None,
                    "source_title": source.title if source else None,
                    "passage": ev.passage,
                })

        # Save assistant message to chat history
        asst_chat = ChatHistory(
            request_id=request_id,
            user_id=user_id,
            role=ChatRole.assistant,
            message=answer,
            citations={"citations": citations_meta, "is_sufficient": is_sufficient},
        )
        db.add(asst_chat)
        db.commit()

        return RAGChatResponse(
            answer=answer,
            citations_used=used_citations,
            citations_metadata=citations_meta,
            is_sufficient=is_sufficient,
        )

    except Exception as e:
        logger.error(f"Error running RAG Assistant: {e}")
        fallback_ans = "There is not enough evidence in the verified document to answer this question."
        asst_chat = ChatHistory(
            request_id=request_id,
            user_id=user_id,
            role=ChatRole.assistant,
            message=fallback_ans,
            citations={"citations": [], "is_sufficient": False},
        )
        db.add(asst_chat)
        db.commit()
        return RAGChatResponse(
            answer=fallback_ans,
            citations_used=[],
            citations_metadata=[],
            is_sufficient=False,
        )
