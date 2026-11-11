"""Unit tests for deterministic explainable job matching scorer (Section 14.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.modules.matching.schemas import MatchingWeights
from app.modules.matching.scorer import (
    CandidateScoringInput,
    JobScoringInput,
    compute_match_score,
    cosine_similarity,
)


def _base_candidate(**overrides: object) -> CandidateScoringInput:
    defaults: dict[str, object] = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "target_roles": ["Backend Engineer", "Software Engineer"],
        "headline": "CS Student building Python and FastAPI APIs",
        "experience_level": "entry_level",
        "years_of_experience": 1.0,
        "degree": "B.Tech Computer Science",
        "location": "Bengaluru",
        "preferred_locations": ["Bengaluru", "Remote"],
        "work_mode_preferences": ["remote", "hybrid"],
        "verified_experience_texts": [
            "Backend Intern Built FastAPI microservices with PostgreSQL and Docker"
        ],
    }
    defaults.update(overrides)
    return CandidateScoringInput(**defaults)  # type: ignore[arg-type]


def _base_job(**overrides: object) -> JobScoringInput:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "title": "Backend Engineer",
        "description": "Build REST APIs using Python, FastAPI, and PostgreSQL.",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker"],
        "experience_level": "entry_level",
        "min_years_experience": 1.0,
        "education_requirements": ["Bachelor in Computer Science"],
        "location": "Bengaluru, India",
        "work_mode": "hybrid",
        "posted_at": now - timedelta(days=1),
        "retrieved_at": now,
    }
    defaults.update(overrides)
    return JobScoringInput(**defaults)  # type: ignore[arg-type]


def test_matching_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="sum to 1.0"):
        MatchingWeights(technical_skill_compatibility=0.9)


def test_exact_skill_match_and_aliases_score_high() -> None:
    cand = _base_candidate(skills=["py", "FastAPI", "postgres", "Docker"])
    job = _base_job()
    res = compute_match_score(candidate=cand, job=job, semantic_similarity=0.92)
    assert res.overall_score >= 85.0
    assert res.missing_skills == []
    assert len(res.matching_skills) >= 3
    assert "semantic_similarity" in res.factor_scores


def test_partial_skill_match_identifies_missing_skills() -> None:
    cand = _base_candidate(skills=["Python"])
    job = _base_job(required_skills=["Python", "FastAPI", "Kubernetes", "Go"])
    res = compute_match_score(candidate=cand, job=job)
    assert res.factor_scores["technical_skill_compatibility"] < 0.5
    assert "FastAPI" in res.missing_skills
    assert "Kubernetes" in res.missing_skills
    assert any("Kubernetes" in item or "FastAPI" in item for item in res.recommended_preparation)


def test_experience_mismatch_reduces_score() -> None:
    junior_cand = _base_candidate(experience_level="student", years_of_experience=0.0)
    senior_job = _base_job(experience_level="senior", min_years_experience=6.0)
    res = compute_match_score(candidate=junior_cand, job=senior_job)
    assert res.factor_scores["experience_level_compatibility"] <= 0.35


def test_location_mismatch_reduces_location_factor() -> None:
    cand = _base_candidate(
        location="Bengaluru",
        preferred_locations=["Bengaluru"],
        work_mode_preferences=["onsite"],
    )
    remote_or_other = _base_job(location="Austin, TX", work_mode="hybrid")
    res = compute_match_score(candidate=cand, job=remote_or_other)
    assert res.factor_scores["location_preferences"] == 0.2


def test_empty_job_description_produces_conservative_baseline() -> None:
    cand = _base_candidate()
    job = _base_job(
        description="",
        required_skills=[],
        preferred_skills=[],
        education_requirements=[],
    )
    res = compute_match_score(candidate=cand, job=job)
    assert res.factor_scores["technical_skill_compatibility"] == 0.4
    assert "conservative" in res.match_explanation.lower()


def test_cosine_similarity_bounds() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([], []) == 0.0
