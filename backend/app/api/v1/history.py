"""History and search API endpoints for previous verification requests."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationResult,
    VerdictLabel,
    InputType,
)
from app.schemas.verification import VerificationRequestResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=list[VerificationRequestResponse])
def get_verification_history(
    q: str | None = Query(None, description="Search claim text or raw text"),
    label: str | None = Query(None, description="Filter by verdict label"),
    input_type: str | None = Query(None, description="Filter by input type (claim, article, file, url)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search and filter past verification requests."""
    query = db.query(VerificationRequest)

    # Restrict to user's requests unless admin
    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if not is_admin:
        query = query.filter(VerificationRequest.user_id == current_user.id)

    # Filter by input_type
    if input_type:
        try:
            it = InputType(input_type.lower())
            query = query.filter(VerificationRequest.input_type == it)
        except ValueError:
            pass

    # Filter by label if specified
    if label:
        matched_label = None
        for lbl in VerdictLabel:
            if lbl.value.lower() == label.lower():
                matched_label = lbl
                break
        if matched_label:
            query = (
                query.join(ExtractedClaim, ExtractedClaim.request_id == VerificationRequest.id)
                .join(VerificationResult, VerificationResult.claim_id == ExtractedClaim.id)
                .filter(VerificationResult.label == matched_label)
            )

    # Text search (searches raw_text or claims)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = (
            query.outerjoin(ExtractedClaim, ExtractedClaim.request_id == VerificationRequest.id)
            .filter(
                or_(
                    VerificationRequest.raw_text.ilike(term),
                    VerificationRequest.source_url.ilike(term),
                    ExtractedClaim.claim_text.ilike(term),
                )
            )
        )

    results = (
        query.distinct()
        .order_by(VerificationRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
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
        for r in results
    ]
