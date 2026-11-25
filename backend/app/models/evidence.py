"""Evidence-related models: sources, passages, evaluations."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RetrievedSource(Base):
    __tablename__ = "retrieved_sources"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("extracted_claims.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    claim = relationship("ExtractedClaim", back_populates="sources")
    evidence_records = relationship(
        "EvidenceRecord", back_populates="source", cascade="all, delete-orphan"
    )
    evaluation = relationship(
        "SourceEvaluation", back_populates="source", uselist=False, cascade="all, delete-orphan"
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("extracted_claims.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("retrieved_sources.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    passage: Mapped[str] = mapped_column(Text, nullable=False)
    nli_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nli_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    claim = relationship("ExtractedClaim", back_populates="evidence_records")
    source = relationship("RetrievedSource", back_populates="evidence_records")


class SourceEvaluation(Base):
    __tablename__ = "source_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("retrieved_sources.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    publisher_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    date_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    corroboration_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    source = relationship("RetrievedSource", back_populates="evaluation")
