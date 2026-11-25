"""Verification-related models: requests, claims, results, reports."""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Enum,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import LONGTEXT

from app.database import Base


class InputType(str, enum.Enum):
    claim = "claim"
    article = "article"
    file = "file"
    url = "url"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class VerdictLabel(str, enum.Enum):
    supported = "Supported"
    contradicted = "Contradicted"
    partially_supported = "Partially Supported"
    insufficient_evidence = "Insufficient Evidence"
    conflicting_evidence = "Conflicting Evidence"


class QueryIntent(str, enum.Enum):
    support = "support"
    contradict = "contradict"


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_type: Mapped[InputType] = mapped_column(
        Enum(InputType), nullable=False
    )
    raw_text: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), nullable=True
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), nullable=False, default=RequestStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="verification_requests")
    documents = relationship(
        "UploadedDocument", back_populates="request", cascade="all, delete-orphan"
    )
    claims = relationship(
        "ExtractedClaim", back_populates="request", cascade="all, delete-orphan"
    )
    agent_logs = relationship(
        "AgentExecutionLog", back_populates="request", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatHistory", back_populates="request", cascade="all, delete-orphan"
    )
    report = relationship(
        "VerificationReport", back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    request = relationship("VerificationRequest", back_populates="documents")


class ExtractedClaim(Base):
    __tablename__ = "extracted_claims"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    request = relationship("VerificationRequest", back_populates="claims")
    search_queries = relationship(
        "SearchQuery", back_populates="claim", cascade="all, delete-orphan"
    )
    sources = relationship(
        "RetrievedSource", back_populates="claim", cascade="all, delete-orphan"
    )
    evidence_records = relationship(
        "EvidenceRecord", back_populates="claim", cascade="all, delete-orphan"
    )
    result = relationship(
        "VerificationResult", back_populates="claim", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_claims_fulltext", "claim_text", mysql_prefix="FULLTEXT"),
    )


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("extracted_claims.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[QueryIntent] = mapped_column(
        Enum(QueryIntent), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    claim = relationship("ExtractedClaim", back_populates="search_queries")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("extracted_claims.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    label: Mapped[VerdictLabel] = mapped_column(
        Enum(VerdictLabel), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    key_passage_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflicts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    claim = relationship("ExtractedClaim", back_populates="result")


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    request = relationship("VerificationRequest", back_populates="report")
