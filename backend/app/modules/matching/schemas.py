"""Pydantic schemas for configurable weighted job matching."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.jobs.schemas import JobSummaryResponse


class MatchingWeights(BaseModel):
    """Configurable weighted scoring distribution summing to 1.0."""

    technical_skill_compatibility: float = Field(default=0.35, ge=0.0, le=1.0)
    job_role_similarity: float = Field(default=0.20, ge=0.0, le=1.0)
    relevant_experience_projects: float = Field(default=0.20, ge=0.0, le=1.0)
    experience_level_compatibility: float = Field(default=0.10, ge=0.0, le=1.0)
    education_requirements: float = Field(default=0.05, ge=0.0, le=1.0)
    location_preferences: float = Field(default=0.05, ge=0.0, le=1.0)
    job_freshness: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self) -> MatchingWeights:
        total = (
            self.technical_skill_compatibility
            + self.job_role_similarity
            + self.relevant_experience_projects
            + self.experience_level_compatibility
            + self.education_requirements
            + self.location_preferences
            + self.job_freshness
        )
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Matching weights must sum to 1.0 (got {total:.4f})")
        return self


class JobMatchResponse(BaseModel):
    """Explainable job match score and gap breakdown."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    algorithm_version: str
    overall_score: float
    factor_scores: dict[str, float]
    weights_used: dict[str, float]
    matching_skills: list[str]
    missing_skills: list[str]
    match_explanation: str
    recommended_preparation: list[str]
    computed_at: datetime


class RecommendedJobItem(BaseModel):
    """Job listing paired with full match evaluation."""

    job: JobSummaryResponse
    match: JobMatchResponse


class RecommendedJobsResponse(BaseModel):
    """Ranked job recommendations for the authenticated user."""

    items: list[RecommendedJobItem]
    total: int
    algorithm_version: str
