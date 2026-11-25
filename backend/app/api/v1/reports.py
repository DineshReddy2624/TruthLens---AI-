"""PDF Report API endpoints."""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, get_current_user_with_query_fallback
from app.models.user import User
from app.models.verification import VerificationRequest, VerificationReport
from app.services.report import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate/{request_id}")
def generate_report(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate or regenerate a PDF report for a verification request."""
    vr = db.query(VerificationRequest).filter_by(id=request_id).first()
    if not vr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if vr.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        pdf_path = generate_pdf_report(db, request_id)
        report = db.query(VerificationReport).filter_by(request_id=request_id).first()
        return {
            "message": "Report generated successfully",
            "pdf_path": pdf_path,
            "summary": report.summary if report else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}",
        )


@router.get("/download/{request_id}")
def download_report(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_query_fallback),
):
    """Download the generated PDF report."""
    vr = db.query(VerificationRequest).filter_by(id=request_id).first()
    if not vr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if vr.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report = db.query(VerificationReport).filter_by(request_id=request_id).first()
    if not report or not report.pdf_path or not os.path.exists(report.pdf_path):
        # Auto-generate if not yet generated
        try:
            pdf_path = generate_pdf_report(db, request_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not generate report: {str(e)}",
            )
    else:
        pdf_path = report.pdf_path

    filename = f"TruthLens_Report_{request_id}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
