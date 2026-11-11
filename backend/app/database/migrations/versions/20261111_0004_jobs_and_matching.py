"""Normalized jobs, saved jobs, and explainable job matches tables.

Revision ID: 20261111_0004
Revises: 20261111_0003
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0004"
down_revision: str | Sequence[str] | None = "20261111_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("canonical_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("work_mode", sa.String(length=32), nullable=False),
        sa.Column("experience_level", sa.String(length=50), nullable=False),
        sa.Column("employment_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements_summary", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_skills", sa.JSON(), nullable=False),
        sa.Column("education_requirements", sa.JSON(), nullable=False),
        sa.Column("min_years_experience", sa.Float(), nullable=True),
        sa.Column("salary_range", sa.String(length=120), nullable=True),
        sa.Column("external_url", sa.String(length=1024), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_vector", sa.JSON(), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_active_posted", "jobs", ["is_active", "posted_at"], unique=False)
    op.create_index(
        op.f("ix_jobs_canonical_fingerprint"), "jobs", ["canonical_fingerprint"], unique=True
    )
    op.create_index(op.f("ix_jobs_company"), "jobs", ["company"], unique=False)
    op.create_index(op.f("ix_jobs_content_hash"), "jobs", ["content_hash"], unique=False)
    op.create_index(op.f("ix_jobs_is_active"), "jobs", ["is_active"], unique=False)
    op.create_index(op.f("ix_jobs_location"), "jobs", ["location"], unique=False)
    op.create_index(op.f("ix_jobs_title"), "jobs", ["title"], unique=False)
    op.create_index(
        "ix_jobs_work_exp", "jobs", ["work_mode", "experience_level"], unique=False
    )

    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_saved_jobs_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_saved_jobs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_jobs")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),
    )
    op.create_index(op.f("ix_saved_jobs_job_id"), "saved_jobs", ["job_id"], unique=False)
    op.create_index(op.f("ix_saved_jobs_user_id"), "saved_jobs", ["user_id"], unique=False)

    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("factor_scores", sa.JSON(), nullable=False),
        sa.Column("weights_used", sa.JSON(), nullable=False),
        sa.Column("matching_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("match_explanation", sa.Text(), nullable=False),
        sa.Column("recommended_preparation", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_matches_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_job_matches_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_matches")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),
    )
    op.create_index(op.f("ix_job_matches_job_id"), "job_matches", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_job_matches_overall_score"), "job_matches", ["overall_score"], unique=False
    )
    op.create_index(op.f("ix_job_matches_user_id"), "job_matches", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_matches_user_id"), table_name="job_matches")
    op.drop_index(op.f("ix_job_matches_overall_score"), table_name="job_matches")
    op.drop_index(op.f("ix_job_matches_job_id"), table_name="job_matches")
    op.drop_table("job_matches")

    op.drop_index(op.f("ix_saved_jobs_user_id"), table_name="saved_jobs")
    op.drop_index(op.f("ix_saved_jobs_job_id"), table_name="saved_jobs")
    op.drop_table("saved_jobs")

    op.drop_index("ix_jobs_work_exp", table_name="jobs")
    op.drop_index(op.f("ix_jobs_title"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_location"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_is_active"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_content_hash"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_company"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_canonical_fingerprint"), table_name="jobs")
    op.drop_index("ix_jobs_active_posted", table_name="jobs")
    op.drop_table("jobs")
