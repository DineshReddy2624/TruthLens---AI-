"""SQLAlchemy ORM models for TruthLens AI."""

from app.database import Base
from app.models.user import User
from app.models.verification import (
    VerificationRequest,
    UploadedDocument,
    ExtractedClaim,
    SearchQuery,
    VerificationResult,
    VerificationReport,
)
from app.models.evidence import (
    RetrievedSource,
    EvidenceRecord,
    SourceEvaluation,
)
from app.models.logs import (
    AgentExecutionLog,
    ChatHistory,
    TrustedSource,
)

__all__ = [
    "Base",
    "User",
    "VerificationRequest",
    "UploadedDocument",
    "ExtractedClaim",
    "SearchQuery",
    "VerificationResult",
    "VerificationReport",
    "RetrievedSource",
    "EvidenceRecord",
    "SourceEvaluation",
    "AgentExecutionLog",
    "ChatHistory",
    "TrustedSource",
]
