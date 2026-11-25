"""LangGraph verification pipeline orchestrating all 9 agents with deterministic supervisor routing."""

import logging
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    RequestStatus,
)
from app.models.evidence import RetrievedSource, EvidenceRecord, SourceEvaluation
from app.agents.claim_extraction import extract_claims
from app.agents.claim_analysis import analyze_claim
from app.agents.research import generate_search_queries
from app.services.retrieval import retrieve_and_store_evidence
from app.agents.source_evaluation import evaluate_source
from app.services.nli import run_nli_on_evidence
from app.agents.fact_verification import verify_claim
from app.agents.contradiction import detect_contradictions
from app.agents.explanation import generate_explanation

logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    """LangGraph state tracking the fact-verification progression."""
    request_id: int
    raw_text: str
    input_type: str
    claims: list[dict[str, Any]]                # list of {"id": int, "claim_text": str, "entities": list}
    analyses: dict[int, dict[str, Any]]         # claim_id -> analysis dict
    queries: dict[int, list[dict[str, str]]]    # claim_id -> list of {"query_text": str, "intent": str}
    evidence_ids: dict[int, list[int]]          # claim_id -> list of evidence_record.id
    source_scores: dict[int, float]             # source_id -> total_score (0-8)
    nli_results: dict[int, dict[str, Any]]      # evidence_id -> {"label": str, "scores": dict}
    verdicts: dict[int, dict[str, Any]]         # claim_id -> {"label": str, "confidence": float, ...}
    conflicts: dict[int, dict[str, Any]]        # claim_id -> conflict dict
    explanations: dict[int, dict[str, Any]]     # claim_id -> explanation dict
    research_retry_count: int                   # number of research retries triggered
    error: str | None


def extract_claims_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 1: Extract checkable factual claims and entities."""
    db: Session = SessionLocal()
    try:
        vr = db.query(VerificationRequest).filter_by(id=state["request_id"]).first()
        if vr:
            vr.status = RequestStatus.running
            db.commit()

        output = extract_claims(
            text=state["raw_text"],
            db=db,
            request_id=state["request_id"],
            custom_llm=custom_llm,
        )

        stored_claims = []
        for c in output.claims:
            claim_rec = ExtractedClaim(
                request_id=state["request_id"],
                claim_text=c.claim_text,
                entities=[e.model_dump() for e in c.entities],
            )
            db.add(claim_rec)
            db.commit()
            db.refresh(claim_rec)

            stored_claims.append({
                "id": claim_rec.id,
                "claim_text": claim_rec.claim_text,
                "entities": claim_rec.entities,
            })

        # If no claims extracted, create one fallback claim from raw text if text is short
        if not stored_claims and len(state["raw_text"].strip()) < 500:
            claim_rec = ExtractedClaim(
                request_id=state["request_id"],
                claim_text=state["raw_text"].strip(),
                entities=[],
            )
            db.add(claim_rec)
            db.commit()
            db.refresh(claim_rec)
            stored_claims.append({
                "id": claim_rec.id,
                "claim_text": claim_rec.claim_text,
                "entities": [],
            })

        return {"claims": stored_claims}
    finally:
        db.close()


def analyze_claims_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 2: Analyze type, domain, time-sensitivity, and verification criteria for each claim."""
    db: Session = SessionLocal()
    analyses = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            claim_rec = db.query(ExtractedClaim).filter_by(id=c_id).first()
            analysis_output = analyze_claim(
                claim_text=c["claim_text"],
                db=db,
                request_id=state["request_id"],
                custom_llm=custom_llm,
            )
            analysis_dict = analysis_output.model_dump()
            analyses[c_id] = analysis_dict

            if claim_rec:
                claim_rec.claim_type = analysis_output.claim_type
                claim_rec.analysis = analysis_dict
                db.add(claim_rec)

        db.commit()
        return {"analyses": analyses}
    finally:
        db.close()


def research_queries_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 3: Generate 4 search queries per claim (2 support, 2 contradict)."""
    db: Session = SessionLocal()
    queries_by_claim = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            analysis = state["analyses"].get(c_id, {})
            res_output = generate_search_queries(
                claim_text=c["claim_text"],
                analysis=analysis,
                db=db,
                request_id=state["request_id"],
                custom_llm=custom_llm,
            )
            queries_by_claim[c_id] = [q.model_dump() for q in res_output.queries]

        return {"queries": queries_by_claim}
    finally:
        db.close()


def retrieve_evidence_node(state: PipelineState, custom_search_client: Any = None) -> dict:
    """Node 4: Search web, clean, chunk, run BM25+ChromaDB hybrid retrieval, and rerank top 5 passages."""
    db: Session = SessionLocal()
    evidence_ids = dict(state.get("evidence_ids", {}))
    try:
        for c in state["claims"]:
            c_id = c["id"]
            c_queries = state["queries"].get(c_id, [])
            passages = retrieve_and_store_evidence(
                db=db,
                claim_id=c_id,
                claim_text=c["claim_text"],
                search_queries=c_queries,
                custom_search_client=custom_search_client,
            )
            evidence_ids[c_id] = [p.passage_id for p in passages if p.passage_id is not None]

        return {"evidence_ids": evidence_ids}
    finally:
        db.close()


def supervisor_check_sources(state: PipelineState) -> str:
    """Supervisor Agent: check if any claim has < 2 independent sources (trigger research_more up to 2 retries)."""
    db: Session = SessionLocal()
    try:
        claims = state.get("claims", [])
        if not claims:
            return "evaluate_sources_node"

        retries = state.get("research_retry_count", 0)
        if retries >= 2:
            return "evaluate_sources_node"

        # Check source count across claims
        for c in claims:
            ev_ids = state.get("evidence_ids", {}).get(c["id"], [])
            if not ev_ids:
                return "research_more"

            sources_count = (
                db.query(EvidenceRecord.source_id)
                .filter(EvidenceRecord.id.in_(ev_ids))
                .distinct()
                .count()
            )
            if sources_count < 2:
                logger.info(f"Claim {c['id']} has {sources_count} source(s) (< 2). Triggering research_more retry #{retries + 1}.")
                return "research_more"

        return "evaluate_sources_node"
    finally:
        db.close()


def increment_retry_node(state: PipelineState) -> dict:
    """Increment research retry counter."""
    return {"research_retry_count": state.get("research_retry_count", 0) + 1}


def evaluate_sources_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 6: Score source credibility (0-8 total) on publisher, date, quality, and corroboration."""
    db: Session = SessionLocal()
    source_scores = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            ev_ids = state.get("evidence_ids", {}).get(c_id, [])
            evidence_records = db.query(EvidenceRecord).filter(EvidenceRecord.id.in_(ev_ids)).all() if ev_ids else []

            seen_sources = set()
            for ev in evidence_records:
                if ev.source_id not in seen_sources:
                    seen_sources.add(ev.source_id)
                    source = db.query(RetrievedSource).filter_by(id=ev.source_id).first()
                    if source:
                        eval_output = evaluate_source(
                            claim_text=c["claim_text"],
                            source=source,
                            sample_content=ev.passage,
                            db=db,
                            request_id=state["request_id"],
                            custom_llm=custom_llm,
                        )
                        source_scores[source.id] = eval_output.total_score

        return {"source_scores": source_scores}
    finally:
        db.close()


def nli_node(state: PipelineState) -> dict:
    """Node 7: Run DeBERTa NLI per (claim, passage) pair."""
    db: Session = SessionLocal()
    nli_results = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            ev_ids = state.get("evidence_ids", {}).get(c_id, [])
            records = db.query(EvidenceRecord).filter(EvidenceRecord.id.in_(ev_ids)).all() if ev_ids else []
            run_nli_on_evidence(db=db, claim_text=c["claim_text"], evidence_records=records)

            for rec in records:
                nli_results[rec.id] = {
                    "label": rec.nli_label,
                    "scores": rec.nli_scores,
                }

        return {"nli_results": nli_results}
    finally:
        db.close()


def verification_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 8: Fact verification agent picks verdict label and computes confidence."""
    db: Session = SessionLocal()
    verdicts = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            ev_ids = state.get("evidence_ids", {}).get(c_id, [])
            records = db.query(EvidenceRecord).filter(EvidenceRecord.id.in_(ev_ids)).all() if ev_ids else []
            analysis_dict = state["analyses"].get(c_id, {})
            analysis_str = f"Type: {analysis_dict.get('claim_type')}, Topic: {analysis_dict.get('topic')}"

            verdict_output, confidence = verify_claim(
                claim_text=c["claim_text"],
                analysis_summary=analysis_str,
                evidence_records=records,
                source_evaluations=state["source_scores"],
                db=db,
                request_id=state["request_id"],
                custom_llm=custom_llm,
            )

            verdicts[c_id] = {
                "label": verdict_output.label,
                "confidence": confidence,
                "key_passage_ids": verdict_output.key_passage_ids,
                "missing_context": verdict_output.missing_context,
                "reasoning": verdict_output.reasoning,
            }

        return {"verdicts": verdicts}
    finally:
        db.close()


def contradiction_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 9: Contradiction detection agent finds differing figures, outdated dates, and explanations."""
    db: Session = SessionLocal()
    conflicts_by_claim = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            ev_ids = state.get("evidence_ids", {}).get(c_id, [])
            records = db.query(EvidenceRecord).filter(EvidenceRecord.id.in_(ev_ids)).all() if ev_ids else []
            conflict_output = detect_contradictions(
                claim_text=c["claim_text"],
                evidence_records=records,
                db=db,
                request_id=state["request_id"],
                custom_llm=custom_llm,
            )
            conflicts_by_claim[c_id] = conflict_output.model_dump()

        return {"conflicts": conflicts_by_claim}
    finally:
        db.close()


def explanation_node(state: PipelineState, custom_llm: Any = None) -> dict:
    """Node 10: Explanation agent generates 3-5 sentence plain-English summary with [1][2] citations."""
    db: Session = SessionLocal()
    explanations = {}
    try:
        for c in state["claims"]:
            c_id = c["id"]
            v_data = state["verdicts"].get(c_id, {})
            ev_ids = state.get("evidence_ids", {}).get(c_id, [])
            records = db.query(EvidenceRecord).filter(EvidenceRecord.id.in_(ev_ids)).all() if ev_ids else []
            c_conflicts = state["conflicts"].get(c_id, {})

            expl_output = generate_explanation(
                claim_text=c["claim_text"],
                label=v_data.get("label", VerdictLabel.insufficient_evidence.value),
                confidence=v_data.get("confidence", 0.5),
                evidence_records=records,
                missing_context=v_data.get("missing_context"),
                conflict_summary=c_conflicts.get("conflict_explanation"),
                db=db,
                request_id=state["request_id"],
                custom_llm=custom_llm,
            )
            explanations[c_id] = expl_output.model_dump()

        return {"explanations": explanations}
    finally:
        db.close()


def persist_results_node(state: PipelineState) -> dict:
    """Node 11: Persist final VerificationResult records to MySQL."""
    db: Session = SessionLocal()
    try:
        for c in state["claims"]:
            c_id = c["id"]
            v = state["verdicts"].get(c_id, {})
            conflicts_dict = state["conflicts"].get(c_id, {})
            expl_dict = state["explanations"].get(c_id, {})

            # Clean / map label to exact enum value
            label_val = VerdictLabel.insufficient_evidence
            for lbl_enum in VerdictLabel:
                if lbl_enum.value.lower() == str(v.get("label", "")).lower():
                    label_val = lbl_enum
                    break

            existing_result = db.query(VerificationResult).filter_by(claim_id=c_id).first()
            if existing_result:
                existing_result.label = label_val
                existing_result.confidence = v.get("confidence", 0.5)
                existing_result.key_passage_ids = v.get("key_passage_ids")
                existing_result.missing_context = v.get("missing_context")
                existing_result.conflicts = conflicts_dict
                existing_result.explanation = expl_dict.get("explanation")
                db.add(existing_result)
            else:
                vres = VerificationResult(
                    claim_id=c_id,
                    label=label_val,
                    confidence=v.get("confidence", 0.5),
                    key_passage_ids=v.get("key_passage_ids"),
                    missing_context=v.get("missing_context"),
                    conflicts=conflicts_dict,
                    explanation=expl_dict.get("explanation"),
                )
                db.add(vres)

        vr = db.query(VerificationRequest).filter_by(id=state["request_id"]).first()
        if vr:
            vr.status = RequestStatus.done
            db.add(vr)

        db.commit()
        return {}
    finally:
        db.close()


def build_pipeline_graph(
    custom_llm: Any = None,
    custom_search_client: Any = None,
) -> StateGraph:
    """Build and compile the LangGraph StateGraph pipeline."""
    graph = StateGraph(PipelineState)

    # Bind dependencies to nodes
    graph.add_node("extract_claims", lambda s: extract_claims_node(s, custom_llm=custom_llm))
    graph.add_node("analyze_claims", lambda s: analyze_claims_node(s, custom_llm=custom_llm))
    graph.add_node("research_queries", lambda s: research_queries_node(s, custom_llm=custom_llm))
    graph.add_node("retrieve_evidence", lambda s: retrieve_evidence_node(s, custom_search_client=custom_search_client))
    graph.add_node("increment_retry", increment_retry_node)
    graph.add_node("evaluate_sources", lambda s: evaluate_sources_node(s, custom_llm=custom_llm))
    graph.add_node("nli_analysis", nli_node)
    graph.add_node("verify_verdicts", lambda s: verification_node(s, custom_llm=custom_llm))
    graph.add_node("detect_contradictions", lambda s: contradiction_node(s, custom_llm=custom_llm))
    graph.add_node("generate_explanations", lambda s: explanation_node(s, custom_llm=custom_llm))
    graph.add_node("persist_results", persist_results_node)

    # Edges
    graph.set_entry_point("extract_claims")
    graph.add_edge("extract_claims", "analyze_claims")
    graph.add_edge("analyze_claims", "research_queries")
    graph.add_edge("research_queries", "retrieve_evidence")

    # Conditional supervisor edge: research_more vs evaluate_sources
    graph.add_conditional_edges(
        "retrieve_evidence",
        supervisor_check_sources,
        {
            "research_more": "increment_retry",
            "evaluate_sources_node": "evaluate_sources",
        },
    )
    graph.add_edge("increment_retry", "research_queries")

    graph.add_edge("evaluate_sources", "nli_analysis")
    graph.add_edge("nli_analysis", "verify_verdicts")
    graph.add_edge("verify_verdicts", "detect_contradictions")
    graph.add_edge("detect_contradictions", "generate_explanations")
    graph.add_edge("generate_explanations", "persist_results")
    graph.add_edge("persist_results", END)

    return graph.compile()


def run_verification_pipeline(
    request_id: int,
    raw_text: str,
    input_type: str = "claim",
    custom_llm: Any = None,
    custom_search_client: Any = None,
) -> dict[str, Any]:
    """Execute the full verification pipeline end-to-end."""
    compiled_graph = build_pipeline_graph(
        custom_llm=custom_llm,
        custom_search_client=custom_search_client,
    )

    initial_state: PipelineState = {
        "request_id": request_id,
        "raw_text": raw_text,
        "input_type": input_type,
        "claims": [],
        "analyses": {},
        "queries": {},
        "evidence_ids": {},
        "source_scores": {},
        "nli_results": {},
        "verdicts": {},
        "conflicts": {},
        "explanations": {},
        "research_retry_count": 0,
        "error": None,
    }

    final_state = compiled_graph.invoke(initial_state)
    return final_state
