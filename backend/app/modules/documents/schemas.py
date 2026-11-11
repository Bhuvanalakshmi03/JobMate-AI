"""Pydantic schemas for tailored resume, cover letter, and application note generation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal["tailored_resume", "cover_letter", "application_note"]
ExportFormat = Literal["pdf", "docx", "md"]


class TailorResumeRequest(BaseModel):
    """Request to generate a job-specific ATS-friendly resume from verified facts."""

    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    focus_instructions: str | None = Field(default=None, max_length=1000)


class CoverLetterRequest(BaseModel):
    """Request to generate a job-specific cover letter grounded in verified facts."""

    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    tone: Literal["professional", "enthusiastic", "concise"] = "professional"
    custom_notes: str | None = Field(default=None, max_length=1000)


class ApplicationNoteRequest(BaseModel):
    """Request to generate a short recruiter/application note."""

    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    max_words: int = Field(default=150, ge=50, le=300)


class DocumentUpdateRequest(BaseModel):
    """Edit generated document content while optionally preserving version history."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_markdown: str | None = Field(default=None, min_length=1, max_length=50000)
    structured_content: dict[str, Any] | None = None
    create_new_version: bool = True


class TailoredExperienceEntry(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    date_range: str | None = Field(default=None, max_length=100)
    bullets: list[str] = Field(default_factory=list, max_length=15)


class TailoredEducationEntry(BaseModel):
    degree: str = Field(min_length=1, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    date_range: str | None = Field(default=None, max_length=100)


class TailoredResumeStructured(BaseModel):
    """Validated structured layout returned for a tailored resume."""

    summary: str = Field(min_length=1, max_length=2500)
    selected_skills: list[str] = Field(default_factory=list, max_length=50)
    experience: list[TailoredExperienceEntry] = Field(default_factory=list, max_length=20)
    projects: list[TailoredExperienceEntry] = Field(default_factory=list, max_length=20)
    education: list[TailoredEducationEntry] = Field(default_factory=list, max_length=10)


class CoverLetterStructured(BaseModel):
    """Validated structured layout returned for a cover letter."""

    subject: str = Field(min_length=1, max_length=255)
    salutation: str = Field(default="Dear Hiring Team,", min_length=1, max_length=255)
    paragraphs: list[str] = Field(min_length=1, max_length=8)
    closing: str = Field(default="Sincerely,", min_length=1, max_length=255)


class ApplicationNoteStructured(BaseModel):
    """Validated structured layout returned for a short application note."""

    note: str = Field(min_length=1, max_length=3000)


class DocumentVersionSummary(BaseModel):
    """Compact version entry for document version history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    is_user_edited: bool
    created_at: datetime


class DocumentResponse(BaseModel):
    """Generated document representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID | None = None
    source_resume_id: uuid.UUID | None = None
    document_type: str
    title: str
    version_group_id: uuid.UUID
    version: int
    content_markdown: str
    structured_content: dict[str, Any] | None = None
    factuality_report: dict[str, Any]
    is_user_edited: bool
    model_used: str | None = None
    tokens_used: int | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Document detail including full version history for the document group."""

    versions: list[DocumentVersionSummary] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """List of generated documents owned by the user."""

    items: list[DocumentResponse]
    total: int
