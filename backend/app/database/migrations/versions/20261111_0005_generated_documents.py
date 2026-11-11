"""Generated documents table for tailored resumes, cover letters, and notes.

Revision ID: 20261111_0005
Revises: 20261111_0004
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0005"
down_revision: str | Sequence[str] | None = "20261111_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_resume_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("version_group_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("factuality_report", sa.JSON(), nullable=False),
        sa.Column("is_user_edited", sa.Boolean(), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_generated_documents_job_id_jobs"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_resume_id"],
            ["resumes.id"],
            name=op.f("fk_generated_documents_source_resume_id_resumes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_generated_documents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_documents")),
        sa.UniqueConstraint("version_group_id", "version", name="uq_generated_docs_group_version"),
    )
    op.create_index(
        op.f("ix_generated_documents_document_type"),
        "generated_documents",
        ["document_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_job_id"), "generated_documents", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_generated_documents_source_resume_id"),
        "generated_documents",
        ["source_resume_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_docs_user_created",
        "generated_documents",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_user_id"), "generated_documents", ["user_id"], unique=False
    )
    op.create_index(
        "ix_generated_docs_user_job", "generated_documents", ["user_id", "job_id"], unique=False
    )
    op.create_index(
        op.f("ix_generated_documents_version_group_id"),
        "generated_documents",
        ["version_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_documents_version_group_id"), table_name="generated_documents")
    op.drop_index("ix_generated_docs_user_job", table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_user_id"), table_name="generated_documents")
    op.drop_index("ix_generated_docs_user_created", table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_source_resume_id"), table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_job_id"), table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_document_type"), table_name="generated_documents")
    op.drop_table("generated_documents")
