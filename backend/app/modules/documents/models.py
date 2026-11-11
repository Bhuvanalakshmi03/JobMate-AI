"""ORM model for versioned generated resumes, cover letters, and application notes."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCTimestampMixin, UUIDPrimaryKeyMixin


class GeneratedDocument(UUIDPrimaryKeyMixin, UTCTimestampMixin, Base):
    """Editable, versioned career document generated strictly from verified facts."""

    __tablename__ = "generated_documents"
    __table_args__ = (
        UniqueConstraint("version_group_id", "version", name="uq_generated_docs_group_version"),
        Index("ix_generated_docs_user_created", "user_id", "created_at"),
        Index("ix_generated_docs_user_job", "user_id", "job_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    factuality_report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
