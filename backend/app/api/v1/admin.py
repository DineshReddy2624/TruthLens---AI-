"""Admin API endpoints for system administration, trusted sources, and agent execution logs."""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.api.deps import require_admin
from app.models.user import User, UserRole
from app.models.verification import VerificationRequest, ExtractedClaim, VerificationResult, VerdictLabel
from app.models.logs import AgentExecutionLog, TrustedSource

router = APIRouter(prefix="/admin", tags=["Admin"])


class UserAdminResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TrustedSourceCreate(BaseModel):
    domain: str
    category: str | None = None
    notes: str | None = None


class TrustedSourceResponse(BaseModel):
    id: int
    domain: str
    category: str | None = None
    notes: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AgentLogResponse(BaseModel):
    id: int
    request_id: int
    agent_name: str
    input_hash: str | None = None
    output: dict[str, Any] | None = None
    latency_ms: int | None = None
    error: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class SystemStatsResponse(BaseModel):
    total_users: int
    total_requests: int
    total_claims: int
    label_distribution: dict[str, int]
    avg_latency_ms: float
    total_agent_runs: int


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all registered users (admin only)."""
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        UserAdminResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Toggle user active/inactive status."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot toggle your own status")

    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


@router.get("/trusted-sources", response_model=list[TrustedSourceResponse])
def list_trusted_sources(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all trusted source domains."""
    return db.query(TrustedSource).order_by(TrustedSource.domain.asc()).all()


@router.post("/trusted-sources", response_model=TrustedSourceResponse, status_code=status.HTTP_201_CREATED)
def add_trusted_source(
    body: TrustedSourceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Add a new trusted domain."""
    domain_clean = body.domain.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()
    existing = db.query(TrustedSource).filter_by(domain=domain_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domain already trusted")

    ts = TrustedSource(
        domain=domain_clean,
        category=body.category,
        notes=body.notes,
        added_by=admin.id,
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts


@router.delete("/trusted-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trusted_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Remove a trusted source domain."""
    ts = db.query(TrustedSource).filter_by(id=source_id).first()
    if not ts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trusted source not found")
    db.delete(ts)
    db.commit()
    return None


@router.get("/logs", response_model=list[AgentLogResponse])
def get_agent_logs(
    agent_name: str | None = Query(None),
    request_id: int | None = Query(None),
    errors_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """View recent agent execution logs with latency, input hash, and errors."""
    query = db.query(AgentExecutionLog)
    if agent_name:
        query = query.filter(AgentExecutionLog.agent_name == agent_name)
    if request_id:
        query = query.filter(AgentExecutionLog.request_id == request_id)
    if errors_only:
        query = query.filter(AgentExecutionLog.error.isnot(None))

    logs = query.order_by(AgentExecutionLog.created_at.desc()).limit(limit).all()
    return logs


@router.get("/stats", response_model=SystemStatsResponse)
def get_system_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve full system stats (users, requests, claims, latency, agent runs)."""
    total_users = db.query(User).count()
    total_requests = db.query(VerificationRequest).count()
    total_claims = db.query(ExtractedClaim).count()

    label_distribution = {lbl.value: 0 for lbl in VerdictLabel}
    results = db.query(VerificationResult.label, func.count(VerificationResult.id)).group_by(VerificationResult.label).all()
    for lbl, count in results:
        lbl_str = lbl.value if hasattr(lbl, "value") else str(lbl)
        if lbl_str in label_distribution:
            label_distribution[lbl_str] = count

    avg_lat = db.query(func.avg(AgentExecutionLog.latency_ms)).scalar() or 0.0
    total_agent_runs = db.query(AgentExecutionLog).count()

    return SystemStatsResponse(
        total_users=total_users,
        total_requests=total_requests,
        total_claims=total_claims,
        label_distribution=label_distribution,
        avg_latency_ms=round(float(avg_lat), 1),
        total_agent_runs=total_agent_runs,
    )
