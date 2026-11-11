"""Pydantic schemas for job discovery, normalization, and saved jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobMatchPreview(BaseModel):
    """Compact match summary embedded in job listings."""

    overall_score: float
    matching_skills: list[str]
    missing_skills: list[str]
    algorithm_version: str


class JobSummaryResponse(BaseModel):
    """Normalized job card representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_provider: str
    title: str
    company: str
    location: str | None = None
    work_mode: str
    experience_level: str
    employment_type: str
    required_skills: list[str]
    preferred_skills: list[str]
    salary_range: str | None = None
    external_url: str
    source_domain: str | None = None
    posted_at: datetime | None = None
    retrieved_at: datetime
    is_active: bool
    is_saved: bool = False
    match_preview: JobMatchPreview | None = None


class JobDetailResponse(JobSummaryResponse):
    """Full normalized job description and requirements."""

    description: str
    requirements_summary: str | None = None
    education_requirements: list[str]
    min_years_experience: float | None = None


class JobSearchResponse(BaseModel):
    """Search response separating source metadata from job items."""

    items: list[JobSummaryResponse]
    total: int
    source: str
    cached: bool = False


class SaveJobRequest(BaseModel):
    """Optional notes when saving a job."""

    notes: str | None = Field(default=None, max_length=2000)


class SavedJobResponse(BaseModel):
    """Saved job confirmation."""

    job_id: uuid.UUID
    is_saved: bool
    notes: str | None = None
    saved_at: datetime
