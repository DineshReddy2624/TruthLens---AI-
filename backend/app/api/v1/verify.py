"""Verification endpoints: submit text, files, URLs, and retrieve claims & analysis."""

import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.api.deps import get_current_user
from app.models.user import User
from app.models.verification import (
    VerificationRequest,
    UploadedDocument,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    InputType,
    RequestStatus,
)
from app.agents.pipeline import run_verification_pipeline
from app.schemas.verification import (
    SubmitTextRequest,
    SubmitUrlRequest,
    VerificationRequestResponse,
    VerificationDetailResponse,
    ExtractedClaimResponse,
    VerificationResultResponse,
    RetrievedSourceResponse,
    SourceEvaluationResponse,
    EvidenceRecordResponse,
    DashboardStatsResponse,
)
from app.services.extractor import (
    extract_text_from_url,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    SSRFSecurityError,
    ExtractorError,
)
from app.agents.claim_extraction import extract_claims
from app.agents.claim_analysis import analyze_claim

router = APIRouter(prefix="/verify", tags=["Verification"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"


def process_and_extract_claims(db: Session, vr: VerificationRequest, raw_text: str):
    """Run full LangGraph verification pipeline end-to-end."""
    try:
        run_verification_pipeline(
            request_id=vr.id,
            raw_text=raw_text,
            input_type=vr.input_type.value,
        )
    except Exception as e:
        logger_error = str(e)
        vr.status = RequestStatus.failed
        db.commit()
        raise e


@router.post("/submit-text", response_model=VerificationRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_text(
    body: SubmitTextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit raw text or a factual claim for extraction and verification."""
    vr = VerificationRequest(
        user_id=current_user.id,
        input_type=body.input_type,
        raw_text=body.text,
        status=RequestStatus.pending,
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)

    process_and_extract_claims(db, vr, body.text)
    db.refresh(vr)

    claims_count = len(vr.claims)
    return VerificationRequestResponse(
        id=vr.id,
        user_id=vr.user_id,
        input_type=vr.input_type.value,
        status=vr.status.value,
        source_url=vr.source_url,
        claims_count=claims_count,
        created_at=vr.created_at,
        updated_at=vr.updated_at,
    )


@router.post("/submit-url", response_model=VerificationRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_url(
    body: SubmitUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a web URL for extraction with SSRF security checks and verification."""
    try:
        extracted_text, title = extract_text_from_url(body.url)
    except SSRFSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: {str(e)}",
        )
    except ExtractorError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract URL text: {str(e)}",
        )

    vr = VerificationRequest(
        user_id=current_user.id,
        input_type=InputType.url,
        raw_text=extracted_text,
        source_url=body.url,
        status=RequestStatus.pending,
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)

    process_and_extract_claims(db, vr, extracted_text)
    db.refresh(vr)

    return VerificationRequestResponse(
        id=vr.id,
        user_id=vr.user_id,
        input_type=vr.input_type.value,
        status=vr.status.value,
        source_url=vr.source_url,
        claims_count=len(vr.claims),
        created_at=vr.created_at,
        updated_at=vr.updated_at,
    )


@router.post("/submit-file", response_model=VerificationRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and extract claims from a PDF, DOCX, or TXT document."""
    settings = get_settings()

    # Validate file extension
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = [e.strip().lower() for e in settings.ALLOWED_EXTENSIONS.split(",")]

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Validate file size
    file_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Extract text based on file format
    try:
        if ext == ".pdf":
            extracted_text = extract_text_from_pdf(file_bytes)
        elif ext == ".docx":
            extracted_text = extract_text_from_docx(file_bytes)
        else:
            extracted_text = extract_text_from_txt(file_bytes)
    except ExtractorError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document parsing error: {str(e)}",
        )

    # Save file to uploads folder
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_storage_name = f"{current_user.id}_{int(os.times().system)}_{filename}"
    storage_path = str(UPLOAD_DIR / safe_storage_name)
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Create verification request
    vr = VerificationRequest(
        user_id=current_user.id,
        input_type=InputType.file,
        raw_text=extracted_text,
        status=RequestStatus.pending,
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)

    # Record uploaded document
    doc = UploadedDocument(
        request_id=vr.id,
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        extracted_text=extracted_text,
    )
    db.add(doc)
    db.commit()

    # Process claims
    process_and_extract_claims(db, vr, extracted_text)
    db.refresh(vr)

    return VerificationRequestResponse(
        id=vr.id,
        user_id=vr.user_id,
        input_type=vr.input_type.value,
        status=vr.status.value,
        source_url=None,
        claims_count=len(vr.claims),
        created_at=vr.created_at,
        updated_at=vr.updated_at,
    )


@router.get("/stats/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve aggregated dashboard statistics for the user."""
    user_requests = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.user_id == current_user.id)
        .order_by(VerificationRequest.created_at.desc())
        .all()
    )
    total_requests = len(user_requests)
    req_ids = [r.id for r in user_requests]

    claims = []
    if req_ids:
        claims = db.query(ExtractedClaim).filter(ExtractedClaim.request_id.in_(req_ids)).all()

    total_claims = len(claims)
    label_distribution = {lbl.value: 0 for lbl in VerdictLabel}
    confidences = []

    for c in claims:
        if c.result:
            lbl = c.result.label.value if hasattr(c.result.label, "value") else str(c.result.label)
            if lbl in label_distribution:
                label_distribution[lbl] += 1
            confidences.append(c.result.confidence)

    avg_confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0

    recent_activity = [
        VerificationRequestResponse(
            id=r.id,
            user_id=r.user_id,
            input_type=r.input_type.value,
            status=r.status.value,
            source_url=r.source_url,
            claims_count=len(r.claims),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in user_requests[:10]
    ]

    return DashboardStatsResponse(
        total_requests=total_requests,
        total_claims=total_claims,
        label_distribution=label_distribution,
        avg_confidence=round(avg_confidence, 3),
        recent_activity=recent_activity,
    )


@router.get("/{request_id}", response_model=VerificationDetailResponse)
def get_verification_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve verification request detail with extracted claims and analysis."""
    vr = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
    if not vr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    # Access control: users can only view their own requests unless admin
    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if vr.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this request")

    claims_responses = []
    for c in vr.claims:
        res_dto = None
        if c.result:
            res_dto = VerificationResultResponse(
                id=c.result.id,
                label=c.result.label.value if hasattr(c.result.label, "value") else str(c.result.label),
                confidence=c.result.confidence,
                key_passage_ids=c.result.key_passage_ids,
                missing_context=c.result.missing_context,
                conflicts=c.result.conflicts,
                explanation=c.result.explanation,
                created_at=c.result.created_at,
            )

        sources_dto = []
        for s in c.sources:
            eval_dto = None
            if s.evaluation:
                eval_dto = SourceEvaluationResponse(
                    id=s.evaluation.id,
                    source_id=s.evaluation.source_id,
                    publisher_score=s.evaluation.publisher_score,
                    date_score=s.evaluation.date_score,
                    quality_score=s.evaluation.quality_score,
                    corroboration_score=s.evaluation.corroboration_score,
                    total_score=s.evaluation.total_score,
                    reason=s.evaluation.reason,
                )
            sources_dto.append(
                RetrievedSourceResponse(
                    id=s.id,
                    url=s.url,
                    domain=s.domain,
                    title=s.title,
                    publisher=s.publisher,
                    published_at=s.published_at,
                    evaluation=eval_dto,
                )
            )

        evidence_dto = [
            EvidenceRecordResponse(
                id=ev.id,
                source_id=ev.source_id,
                passage=ev.passage,
                nli_label=ev.nli_label,
                nli_scores=ev.nli_scores,
                rank_score=ev.rank_score,
            )
            for ev in c.evidence_records
        ]

        claims_responses.append(
            ExtractedClaimResponse(
                id=c.id,
                claim_text=c.claim_text,
                claim_type=c.claim_type,
                entities=c.entities,
                analysis=c.analysis,
                result=res_dto,
                sources=sources_dto,
                evidence_records=evidence_dto,
                created_at=c.created_at,
            )
        )

    preview = vr.raw_text[:300] if vr.raw_text else None

    return VerificationDetailResponse(
        id=vr.id,
        user_id=vr.user_id,
        input_type=vr.input_type.value,
        status=vr.status.value,
        source_url=vr.source_url,
        raw_text_preview=preview,
        claims=claims_responses,
        created_at=vr.created_at,
        updated_at=vr.updated_at,
    )


@router.get("", response_model=list[VerificationRequestResponse])
def list_verification_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent verification requests for the authenticated user."""
    requests = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.user_id == current_user.id)
        .order_by(VerificationRequest.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        VerificationRequestResponse(
            id=r.id,
            user_id=r.user_id,
            input_type=r.input_type.value,
            status=r.status.value,
            source_url=r.source_url,
            claims_count=len(r.claims),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in requests
    ]
