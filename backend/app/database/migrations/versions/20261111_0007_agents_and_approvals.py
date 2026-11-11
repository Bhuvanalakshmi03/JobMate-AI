"""Workflow runs and human approvals tables.

Revision ID: 20261111_0007
Revises: 20261111_0006
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0007"
down_revision: str | Sequence[str] | None = "20261111_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("user_request", sa.Text(), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("state_snapshot", sa.JSON(), nullable=False),
        sa.Column("agent_outputs", sa.JSON(), nullable=False),
        sa.Column("validation_results", sa.JSON(), nullable=False),
        sa.Column("pending_approval_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("execution_trace", sa.JSON(), nullable=False),
        sa.Column("total_tokens_used", sa.Integer(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_workflow_runs_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_workflow_runs_job_id_jobs"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workflow_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
    )
    op.create_index(
        op.f("ix_workflow_runs_application_id"), "workflow_runs", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_workflow_runs_job_id"), "workflow_runs", ["job_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_status"), "workflow_runs", ["status"], unique=False)
    op.create_index(
        op.f("ix_workflow_runs_task_type"), "workflow_runs", ["task_type"], unique=False
    )
    op.create_index(op.f("ix_workflow_runs_user_id"), "workflow_runs", ["user_id"], unique=False)
    op.create_index(
        "ix_workflow_runs_user_status", "workflow_runs", ["user_id", "status"], unique=False
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_destination", sa.String(length=1024), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_approvals_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_approvals_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_approvals_workflow_run_id_workflow_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )
    op.create_index(
        op.f("ix_approvals_action_type"), "approvals", ["action_type"], unique=False
    )
    op.create_index(
        op.f("ix_approvals_application_id"), "approvals", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_approvals_status"), "approvals", ["status"], unique=False)
    op.create_index(op.f("ix_approvals_user_id"), "approvals", ["user_id"], unique=False)
    op.create_index("ix_approvals_user_status", "approvals", ["user_id", "status"], unique=False)
    op.create_index("ix_approvals_workflow_run", "approvals", ["workflow_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_approvals_workflow_run", table_name="approvals")
    op.drop_index("ix_approvals_user_status", table_name="approvals")
    op.drop_index(op.f("ix_approvals_user_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_status"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_application_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_action_type"), table_name="approvals")
    op.drop_table("approvals")

    op.drop_index("ix_workflow_runs_user_status", table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_user_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_task_type"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_status"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_job_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_application_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
