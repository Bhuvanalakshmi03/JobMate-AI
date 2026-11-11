"""Applications and application_history tables.

Revision ID: 20261111_0006
Revises: 20261111_0005
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0006"
down_revision: str | Sequence[str] | None = "20261111_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tailored_resume_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("cover_letter_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("role_title", sa.String(length=255), nullable=False),
        sa.Column("job_url", sa.String(length=1024), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["cover_letter_id"],
            ["generated_documents.id"],
            name=op.f("fk_applications_cover_letter_id_generated_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_applications_job_id_jobs"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["tailored_resume_id"],
            ["generated_documents.id"],
            name=op.f("fk_applications_tailored_resume_id_generated_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_applications_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index(op.f("ix_applications_deadline_at"), "applications", ["deadline_at"], unique=False)
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)
    op.create_index(
        "ix_applications_user_deadline", "applications", ["user_id", "deadline_at"], unique=False
    )
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_index(
        "ix_applications_user_status", "applications", ["user_id", "status"], unique=False
    )

    op.create_table(
        "application_history",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_history_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_history_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_history")),
    )
    op.create_index(
        "ix_app_history_app_changed",
        "application_history",
        ["application_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_history_application_id"),
        "application_history",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_history_user_id"), "application_history", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_application_history_user_id"), table_name="application_history")
    op.drop_index(op.f("ix_application_history_application_id"), table_name="application_history")
    op.drop_index("ix_app_history_app_changed", table_name="application_history")
    op.drop_table("application_history")

    op.drop_index("ix_applications_user_status", table_name="applications")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index("ix_applications_user_deadline", table_name="applications")
    op.drop_index(op.f("ix_applications_status"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_deadline_at"), table_name="applications")
    op.drop_table("applications")
