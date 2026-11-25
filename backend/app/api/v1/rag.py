"""RAG Assistant API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.verification import VerificationRequest
from app.models.logs import ChatHistory
from app.schemas.verification import RAGChatRequest, RAGChatResponse, ChatHistoryItem
from app.services.rag import answer_rag_question

router = APIRouter(prefix="/rag", tags=["RAG Assistant"])


@router.post("/chat", response_model=RAGChatResponse)
def rag_chat(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask an interactive question about a verified document with citations."""
    vr = db.query(VerificationRequest).filter_by(id=body.request_id).first()
    if not vr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if vr.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return answer_rag_question(
        db=db,
        request_id=body.request_id,
        user_id=current_user.id,
        user_message=body.message,
    )


@router.get("/history/{request_id}", response_model=list[ChatHistoryItem])
def get_chat_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chat history for a verification request."""
    vr = db.query(VerificationRequest).filter_by(id=request_id).first()
    if not vr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    is_admin = (current_user.role.value == "admin") if hasattr(current_user.role, "value") else (str(current_user.role) == "admin")
    if vr.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    messages = (
        db.query(ChatHistory)
        .filter_by(request_id=request_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )

    return [
        ChatHistoryItem(
            id=m.id,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            message=m.message,
            citations=m.citations.get("citations") if isinstance(m.citations, dict) else None,
            created_at=m.created_at,
        )
        for m in messages
    ]
