"""ORM model for persisted explainable job matching evaluations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, UTCTimestampMixin, UUIDPrimaryKeyMixin, utc_now


class JobMatch(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Persisted factor-by-factor match evaluation between a user and a normalized job."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0.0")
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    factor_scores: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    weights_used: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    matching_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    match_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_preparation: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
