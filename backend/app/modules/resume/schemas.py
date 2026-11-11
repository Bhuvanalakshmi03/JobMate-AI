"""Pydantic schemas for resume upload, AI extraction, analysis, and fact verification."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ParseStatus = Literal["uploaded", "parsing", "parsed", "analyzed", "failed"]
FactType = Literal[
    "personal_info",
    "education",
    "experience",
    "internship",
    "project",
    "skill",
    "certification",
    "achievement",
]
VerificationAction = Literal["verify", "edit", "reject"]
VerificationStatus = Literal["pending", "verified", "edited", "rejected"]


_FACT_TYPE_ALIASES: dict[str, FactType] = {
    "award": "achievement",
    "awards": "achievement",
    "honor": "achievement",
    "honors": "achievement",
    "summary": "personal_info",
    "profile": "personal_info",
    "work": "experience",
    "work_experience": "experience",
    "employment": "experience",
    "course": "certification",
    "training": "certification",
    "certificate": "certification",
    "skills": "skill",
    "projects": "project",
}


class ExtractedFactCandidate(BaseModel):
    """Single structured fact extracted and validated from resume text."""

    fact_type: FactType
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    start_date: str | None = Field(default=None, max_length=50)
    end_date: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=4000)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    source_section: str | None = Field(default=None, max_length=100)
    evidence_excerpt: str | None = Field(default=None, max_length=1000)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator("fact_type", mode="before")
    @classmethod
    def normalize_fact_type(cls, value: object) -> object:
        if isinstance(value, str):
            norm = value.strip().lower().replace(" ", "_")
            return _FACT_TYPE_ALIASES.get(norm, norm)
        return value

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: object) -> object:
        if isinstance(value, (int, float)) and value > 1.0 and value <= 100.0:
            return round(float(value) / 100.0, 3)
        return value

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Fact title cannot be empty")
        return cleaned

    @field_validator("structured_data", mode="before")
    @classmethod
    def coerce_null_structured_data(cls, value: object) -> object:
        return {} if value is None else value


class ExtractedResumePayload(BaseModel):
    """Validated JSON structure returned by the Resume Analyst Agent."""

    completeness_score: float = Field(ge=0.0, le=100.0)
    overall_assessment: str = Field(min_length=1, max_length=2000)
    strengths: list[str] = Field(default_factory=list, max_length=20)
    weaknesses: list[str] = Field(default_factory=list, max_length=20)
    missing_skills: list[str] = Field(default_factory=list, max_length=30)
    recommendations: list[str] = Field(default_factory=list, max_length=20)
    facts: list[ExtractedFactCandidate] = Field(default_factory=list, max_length=150)


class ResumeSummaryResponse(BaseModel):
    """Compact resume projection for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    file_extension: str
    file_size_bytes: int
    page_count: int | None = None
    parse_status: str
    completeness_score: float | None = None
    error_message: str | None = None
    analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ResumeDetailResponse(ResumeSummaryResponse):
    """Detailed resume view including extracted text preview and analysis summary."""

    extracted_text: str | None = None
    analysis_summary: dict[str, Any] | None = None
    fact_count: int = 0
    verified_fact_count: int = 0


class ResumeFactResponse(BaseModel):
    """Stored resume fact returned for user verification and review."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    fact_type: str
    title: str
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    structured_data: dict[str, Any] | None = None
    source_section: str | None = None
    evidence_excerpt: str | None = None
    confidence: float
    verification_status: str
    is_verified: bool
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ResumeAnalysisResponse(BaseModel):
    """Complete analysis and extracted facts payload for user review."""

    resume: ResumeSummaryResponse
    completeness_score: float | None = None
    analysis_summary: dict[str, Any] | None = None
    facts: list[ResumeFactResponse]


class FactPatchItem(BaseModel):
    """User verification, correction, or rejection update for a single extracted fact."""

    fact_id: uuid.UUID
    action: VerificationAction
    title: str | None = Field(default=None, min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    start_date: str | None = Field(default=None, max_length=50)
    end_date: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=4000)
    structured_data: dict[str, Any] | None = None


class ResumeFactsPatchRequest(BaseModel):
    """Batch verification and optional career-profile synchronization request."""

    updates: list[FactPatchItem] = Field(min_length=1, max_length=100)
    sync_to_profile: bool = True


class ResumeFactsPatchResponse(BaseModel):
    """Result of applying fact verifications and profile synchronization."""

    facts: list[ResumeFactResponse]
    verified_count: int
    synced_to_profile: bool
    synced_skills_count: int


class ResumeListResponse(BaseModel):
    """Paginated list of user resumes."""

    items: list[ResumeSummaryResponse]
    total: int
