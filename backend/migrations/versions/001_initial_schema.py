"""Initial schema with all 13 tables.

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", name="userrole"), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- verification_requests ---
    op.create_table(
        "verification_requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input_type", sa.Enum("claim", "article", "file", "url", name="inputtype"), nullable=False),
        sa.Column("raw_text", mysql.LONGTEXT, nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "done", "failed", name="requeststatus"), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_vr_user_id", "verification_requests", ["user_id"])

    # --- uploaded_documents ---
    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("extracted_text", mysql.LONGTEXT, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_ud_request_id", "uploaded_documents", ["request_id"])

    # --- extracted_claims ---
    op.create_table(
        "extracted_claims",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_text", sa.Text, nullable=False),
        sa.Column("claim_type", sa.String(100), nullable=True),
        sa.Column("entities", sa.JSON, nullable=True),
        sa.Column("analysis", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_ec_request_id", "extracted_claims", ["request_id"])
    op.execute("ALTER TABLE extracted_claims ADD FULLTEXT INDEX ix_claims_fulltext (claim_text)")

    # --- search_queries ---
    op.create_table(
        "search_queries",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.BigInteger, sa.ForeignKey("extracted_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("intent", sa.Enum("support", "contradict", name="queryintent"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_sq_claim_id", "search_queries", ["claim_id"])

    # --- retrieved_sources ---
    op.create_table(
        "retrieved_sources",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.BigInteger, sa.ForeignKey("extracted_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("title", sa.String(1024), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("fetched_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_rs_claim_id", "retrieved_sources", ["claim_id"])

    # --- evidence_records ---
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.BigInteger, sa.ForeignKey("extracted_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.BigInteger, sa.ForeignKey("retrieved_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passage", sa.Text, nullable=False),
        sa.Column("nli_label", sa.String(50), nullable=True),
        sa.Column("nli_scores", sa.JSON, nullable=True),
        sa.Column("rank_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_er_claim_id", "evidence_records", ["claim_id"])
    op.create_index("ix_er_source_id", "evidence_records", ["source_id"])

    # --- source_evaluations ---
    op.create_table(
        "source_evaluations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.BigInteger, sa.ForeignKey("retrieved_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("publisher_score", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("date_score", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("quality_score", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("corroboration_score", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("total_score", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_se_source_id", "source_evaluations", ["source_id"], unique=True)

    # --- verification_results ---
    op.create_table(
        "verification_results",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.BigInteger, sa.ForeignKey("extracted_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "label",
            sa.Enum("Supported", "Contradicted", "Partially Supported", "Insufficient Evidence", "Conflicting Evidence", name="verdictlabel"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("key_passage_ids", sa.JSON, nullable=True),
        sa.Column("missing_context", sa.Text, nullable=True),
        sa.Column("conflicts", sa.JSON, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_vres_claim_id", "verification_results", ["claim_id"], unique=True)
    op.create_index("ix_vres_label", "verification_results", ["label"])

    # --- agent_execution_logs ---
    op.create_table(
        "agent_execution_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("output", sa.JSON, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_ael_request_id", "agent_execution_logs", ["request_id"])

    # --- chat_history ---
    op.create_table(
        "chat_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", name="chatrole"), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("citations", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_ch_request_id", "chat_history", ["request_id"])
    op.create_index("ix_ch_user_id", "chat_history", ["user_id"])

    # --- verification_reports ---
    op.create_table(
        "verification_reports",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.BigInteger, sa.ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pdf_path", sa.String(1024), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_vrep_request_id", "verification_reports", ["request_id"], unique=True)

    # --- trusted_sources ---
    op.create_table(
        "trusted_sources",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("added_by", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_ts_domain", "trusted_sources", ["domain"], unique=True)


def downgrade() -> None:
    op.drop_table("trusted_sources")
    op.drop_table("verification_reports")
    op.drop_table("chat_history")
    op.drop_table("agent_execution_logs")
    op.drop_table("verification_results")
    op.drop_table("source_evaluations")
    op.drop_table("evidence_records")
    op.drop_table("retrieved_sources")
    op.drop_table("search_queries")
    op.drop_table("extracted_claims")
    op.drop_table("uploaded_documents")
    op.drop_table("verification_requests")
    op.drop_table("users")
