"""Resumes and extracted verifiable resume facts tables.

Revision ID: 20261111_0003
Revises: 20261111_0002
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0003"
down_revision: str | Sequence[str] | None = "20261111_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("file_extension", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("analysis_summary", sa.JSON(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_resumes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resumes")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_resumes_storage_key")),
    )
    op.create_index(op.f("ix_resumes_parse_status"), "resumes", ["parse_status"], unique=False)
    op.create_index(op.f("ix_resumes_sha256_hash"), "resumes", ["sha256_hash"], unique=False)
    op.create_index("ix_resumes_user_created", "resumes", ["user_id", "created_at"], unique=False)
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)
    op.create_index("ix_resumes_user_sha256", "resumes", ["user_id", "sha256_hash"], unique=False)

    op.create_table(
        "resume_facts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("resume_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("fact_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.String(length=50), nullable=True),
        sa.Column("end_date", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("source_section", sa.String(length=100), nullable=True),
        sa.Column("evidence_excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name=op.f("fk_resume_facts_resume_id_resumes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_resume_facts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resume_facts")),
    )
    op.create_index(op.f("ix_resume_facts_fact_type"), "resume_facts", ["fact_type"], unique=False)
    op.create_index(
        op.f("ix_resume_facts_is_verified"), "resume_facts", ["is_verified"], unique=False
    )
    op.create_index(op.f("ix_resume_facts_resume_id"), "resume_facts", ["resume_id"], unique=False)
    op.create_index(
        "ix_resume_facts_resume_type", "resume_facts", ["resume_id", "fact_type"], unique=False
    )
    op.create_index(op.f("ix_resume_facts_user_id"), "resume_facts", ["user_id"], unique=False)
    op.create_index(
        "ix_resume_facts_user_verified", "resume_facts", ["user_id", "is_verified"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_resume_facts_user_verified", table_name="resume_facts")
    op.drop_index(op.f("ix_resume_facts_user_id"), table_name="resume_facts")
    op.drop_index("ix_resume_facts_resume_type", table_name="resume_facts")
    op.drop_index(op.f("ix_resume_facts_resume_id"), table_name="resume_facts")
    op.drop_index(op.f("ix_resume_facts_is_verified"), table_name="resume_facts")
    op.drop_index(op.f("ix_resume_facts_fact_type"), table_name="resume_facts")
    op.drop_table("resume_facts")

    op.drop_index("ix_resumes_user_sha256", table_name="resumes")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_index("ix_resumes_user_created", table_name="resumes")
    op.drop_index(op.f("ix_resumes_sha256_hash"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_parse_status"), table_name="resumes")
    op.drop_table("resumes")
