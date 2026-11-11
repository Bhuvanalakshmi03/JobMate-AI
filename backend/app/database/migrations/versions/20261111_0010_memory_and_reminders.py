"""Consent-gated career memory and deduplicated reminders tables.

Revision ID: 20261111_0010
Revises: 20261111_0009
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0010"
down_revision: str | Sequence[str] | None = "20261111_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_memory",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("memory_key", sa.String(length=120), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_career_memory_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_memory")),
        sa.UniqueConstraint("user_id", "memory_key", name="uq_career_memory_user_key"),
    )
    op.create_index(op.f("ix_career_memory_user_id"), "career_memory", ["user_id"], unique=False)
    op.create_index(
        "ix_career_memory_user_active",
        "career_memory",
        ["user_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("reminder_type", sa.String(length=32), nullable=False),
        sa.Column("dedup_key", sa.String(length=160), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_timezone", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_reminders_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_reminders_job_id_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reminders_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminders")),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_reminders_user_dedup"),
    )
    op.create_index(op.f("ix_reminders_user_id"), "reminders", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_reminders_application_id"), "reminders", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_reminders_status"), "reminders", ["status"], unique=False)
    op.create_index(
        "ix_reminders_user_status_sched",
        "reminders",
        ["user_id", "status", "scheduled_for"],
        unique=False,
    )
    op.create_index(
        "ix_reminders_due_lookup",
        "reminders",
        ["status", "scheduled_for"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reminders_due_lookup", table_name="reminders")
    op.drop_index("ix_reminders_user_status_sched", table_name="reminders")
    op.drop_index(op.f("ix_reminders_status"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_application_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_table("reminders")
    op.drop_index("ix_career_memory_user_active", table_name="career_memory")
    op.drop_index(op.f("ix_career_memory_user_id"), table_name="career_memory")
    op.drop_table("career_memory")
