"""Deterministic explainable weighted job matching scorer (independent of LLM)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.matching.schemas import MatchingWeights

ALGORITHM_VERSION = "v1.0.0"

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")

_SKILL_ALIASES: dict[str, str] = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "aws cloud": "aws",
    "ml": "machine learning",
    "dl": "deep learning",
}

_EXPERIENCE_LEVEL_RANK: dict[str, float] = {
    "student": 0.0,
    "intern": 0.5,
    "entry_level": 1.0,
    "junior": 2.0,
    "mid_level": 3.0,
    "senior": 4.0,
}

_STOP_WORDS = frozenset(
    {
        "and",
        "the",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "will",
        "are",
        "our",
        "you",
        "your",
        "using",
        "work",
        "team",
        "role",
        "job",
    }
)


def normalize_skill(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw).strip().lower()
    return _SKILL_ALIASES.get(cleaned, cleaned)


def _tokenize(text: str) -> set[str]:
    return {
        tok
        for tok in _TOKEN_RE.findall(text.lower())
        if len(tok) >= 2 and tok not in _STOP_WORDS
    }


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute bounded cosine similarity normalized to [0, 1]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    raw = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, raw))


@dataclass(frozen=True, slots=True)
class CandidateScoringInput:
    """Verified user profile, skills, and verified experience inputs (no protected attributes)."""

    skills: list[str]
    target_roles: list[str]
    headline: str | None
    experience_level: str | None
    years_of_experience: float | None
    degree: str | None
    location: str | None
    preferred_locations: list[str]
    work_mode_preferences: list[str]
    verified_experience_texts: list[str]


@dataclass(frozen=True, slots=True)
class JobScoringInput:
    """Normalized job target fields for deterministic scoring."""

    title: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_level: str
    min_years_experience: float | None
    education_requirements: list[str]
    location: str | None
    work_mode: str
    posted_at: datetime | None
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class MatchScoreResult:
    """Explainable factor-by-factor match evaluation."""

    algorithm_version: str
    overall_score: float
    factor_scores: dict[str, float]
    weights_used: dict[str, float]
    matching_skills: list[str]
    missing_skills: list[str]
    match_explanation: str
    recommended_preparation: list[str]


def _score_technical_skills(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    job_description: str,
) -> tuple[float, list[str], list[str]]:
    cand_map: dict[str, str] = {}
    for skill in candidate_skills:
        norm = normalize_skill(skill)
        if norm and norm not in cand_map:
            cand_map[norm] = skill.strip()

    req_map: dict[str, str] = {}
    for skill in required_skills:
        norm = normalize_skill(skill)
        if norm and norm not in req_map:
            req_map[norm] = skill.strip()

    pref_map: dict[str, str] = {}
    for skill in preferred_skills:
        norm = normalize_skill(skill)
        if norm and norm not in pref_map and norm not in req_map:
            pref_map[norm] = skill.strip()

    if not req_map:
        desc_tokens = _tokenize(job_description)
        if not desc_tokens:
            return 0.4, [], []
        matched_from_desc = [
            display for norm, display in cand_map.items() if norm in job_description.lower()
        ]
        if not cand_map:
            return 0.2, [], []
        ratio = min(1.0, len(matched_from_desc) / max(1, min(5, len(cand_map))))
        return round(0.35 + 0.65 * ratio, 4), matched_from_desc, []

    matched_req = [display for norm, display in req_map.items() if norm in cand_map]
    missing_req = [display for norm, display in req_map.items() if norm not in cand_map]
    matched_pref = [display for norm, display in pref_map.items() if norm in cand_map]

    req_ratio = len(matched_req) / len(req_map)
    pref_bonus = 0.0
    if pref_map:
        pref_bonus = 0.1 * (len(matched_pref) / len(pref_map))

    score = min(1.0, req_ratio * 0.9 + pref_bonus) if pref_map else req_ratio
    all_matched = matched_req + [s for s in matched_pref if s not in matched_req]
    return round(score, 4), all_matched, missing_req


def _score_role_similarity(
    *,
    target_roles: list[str],
    headline: str | None,
    job_title: str,
    semantic_similarity: float | None,
) -> float:
    job_tokens = _tokenize(job_title)
    profile_phrases = list(target_roles)
    if headline:
        profile_phrases.append(headline)

    lexical_score = 0.3
    if job_tokens and profile_phrases:
        best_overlap = 0.0
        for phrase in profile_phrases:
            p_tokens = _tokenize(phrase)
            if not p_tokens:
                continue
            overlap = len(job_tokens & p_tokens) / len(job_tokens | p_tokens)
            best_overlap = max(best_overlap, overlap)
        lexical_score = min(1.0, best_overlap * 1.4)

    if semantic_similarity is not None:
        return round(max(0.0, min(1.0, 0.55 * lexical_score + 0.45 * semantic_similarity)), 4)
    return round(lexical_score, 4)


def _score_experience_and_projects(
    *,
    verified_texts: list[str],
    job_title: str,
    job_description: str,
    required_skills: list[str],
) -> float:
    if not verified_texts:
        return 0.2
    job_corpus = f"{job_title} {job_description} {' '.join(required_skills)}".strip()
    job_tokens = _tokenize(job_corpus)
    if not job_tokens:
        return 0.4

    exp_tokens = _tokenize(" ".join(verified_texts))
    if not exp_tokens:
        return 0.2
    overlap = len(exp_tokens & job_tokens)
    target_denominator = max(4, min(20, len(job_tokens)))
    return round(min(1.0, overlap / target_denominator), 4)


def _score_experience_level(
    *,
    user_level: str | None,
    user_years: float | None,
    job_level: str,
    job_min_years: float | None,
) -> float:
    if job_level == "unknown" and job_min_years is None:
        return 0.75

    score = 0.7
    if user_level and job_level in _EXPERIENCE_LEVEL_RANK and user_level in _EXPERIENCE_LEVEL_RANK:
        diff = abs(_EXPERIENCE_LEVEL_RANK[user_level] - _EXPERIENCE_LEVEL_RANK[job_level])
        if diff <= 0.5:
            score = 1.0
        elif diff <= 1.0:
            score = 0.75
        elif diff <= 2.0:
            score = 0.45
        else:
            score = 0.2

    if job_min_years is not None and user_years is not None:
        if user_years >= job_min_years:
            years_score = 1.0
        elif job_min_years - user_years <= 1.0:
            years_score = 0.7
        else:
            years_score = 0.25
        score = 0.5 * score + 0.5 * years_score

    return round(score, 4)


def _score_education(user_degree: str | None, job_education_reqs: list[str]) -> float:
    if not job_education_reqs:
        return 1.0
    if not user_degree or not user_degree.strip():
        return 0.4
    user_tokens = _tokenize(user_degree)
    req_tokens = _tokenize(" ".join(job_education_reqs))
    if not req_tokens:
        return 1.0
    if user_tokens & req_tokens:
        return 1.0
    if any(k in user_degree.lower() for k in ("b.tech", "b.e", "b.s", "bachelor", "master", "m.s")):
        return 0.75
    return 0.45


def _score_location(
    *,
    preferred_locations: list[str],
    user_location: str | None,
    work_mode_prefs: list[str],
    job_location: str | None,
    job_work_mode: str,
) -> float:
    pref_locs = [loc.strip().lower() for loc in preferred_locations if loc.strip()]
    if user_location and user_location.strip():
        pref_locs.append(user_location.strip().lower())

    mode_prefs = {m.strip().lower() for m in work_mode_prefs if m.strip()}
    job_loc_norm = (job_location or "").strip().lower()

    if job_work_mode == "remote":
        if not mode_prefs or "remote" in mode_prefs or "remote" in pref_locs:
            return 1.0
        return 0.7

    mode_match = not mode_prefs or job_work_mode == "unknown" or job_work_mode in mode_prefs
    loc_match = not pref_locs or (
        bool(job_loc_norm)
        and any(pref in job_loc_norm or job_loc_norm in pref for pref in pref_locs)
    )

    if mode_match and loc_match:
        return 1.0
    if mode_match or loc_match:
        return 0.65
    return 0.2


def _score_freshness(posted_at: datetime | None, retrieved_at: datetime) -> float:
    ref = posted_at or retrieved_at
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    age_days = max(0.0, (datetime.now(UTC) - ref).total_seconds() / 86400.0)
    if age_days <= 3:
        return 1.0
    if age_days <= 14:
        return 0.85
    if age_days <= 30:
        return 0.65
    return 0.35


def compute_match_score(
    *,
    candidate: CandidateScoringInput,
    job: JobScoringInput,
    weights: MatchingWeights | None = None,
    semantic_similarity: float | None = None,
) -> MatchScoreResult:
    """Calculate explainable weighted match score M = sum(w_i * s_i) * 100."""
    resolved_weights = weights or MatchingWeights()

    skill_score, matching_skills, missing_skills = _score_technical_skills(
        candidate.skills,
        job.required_skills,
        job.preferred_skills,
        job.description,
    )
    role_score = _score_role_similarity(
        target_roles=candidate.target_roles,
        headline=candidate.headline,
        job_title=job.title,
        semantic_similarity=semantic_similarity,
    )
    exp_proj_score = _score_experience_and_projects(
        verified_texts=candidate.verified_experience_texts,
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills,
    )
    exp_level_score = _score_experience_level(
        user_level=candidate.experience_level,
        user_years=candidate.years_of_experience,
        job_level=job.experience_level,
        job_min_years=job.min_years_experience,
    )
    edu_score = _score_education(candidate.degree, job.education_requirements)
    loc_score = _score_location(
        preferred_locations=candidate.preferred_locations,
        user_location=candidate.location,
        work_mode_prefs=candidate.work_mode_preferences,
        job_location=job.location,
        job_work_mode=job.work_mode,
    )
    fresh_score = _score_freshness(job.posted_at, job.retrieved_at)

    factor_scores: dict[str, float] = {
        "technical_skill_compatibility": skill_score,
        "job_role_similarity": role_score,
        "relevant_experience_projects": exp_proj_score,
        "experience_level_compatibility": exp_level_score,
        "education_requirements": edu_score,
        "location_preferences": loc_score,
        "job_freshness": fresh_score,
    }
    if semantic_similarity is not None:
        factor_scores["semantic_similarity"] = round(semantic_similarity, 4)

    weights_dict = resolved_weights.model_dump()
    weighted_sum = sum(weights_dict[key] * factor_scores[key] for key in weights_dict)
    overall_score = round(max(0.0, min(100.0, weighted_sum * 100.0)), 1)

    explanation_parts = [
        f"Overall match score {overall_score}% ({ALGORITHM_VERSION}):",
        f"Technical skills fit {int(skill_score * 100)}%"
        + (f" ({len(matching_skills)} matched)" if matching_skills else ""),
        f"Role alignment {int(role_score * 100)}%",
        f"Verified projects/experience fit {int(exp_proj_score * 100)}%",
        f"Location/work-mode fit {int(loc_score * 100)}%.",
    ]
    if missing_skills:
        explanation_parts.append(f"Missing skills: {', '.join(missing_skills[:6])}.")
    if not job.description.strip() and not job.required_skills:
        explanation_parts.append("Job description was minimal, so skill inference is conservative.")

    prep_items: list[str] = [
        f"Build hands-on familiarity with {skill}" for skill in missing_skills[:5]
    ]
    if exp_proj_score < 0.5:
        prep_items.append(f"Highlight verified projects relevant to {job.title}")
    if not prep_items:
        prep_items.append(f"Review core system design and behavioral examples for {job.title}")

    return MatchScoreResult(
        algorithm_version=ALGORITHM_VERSION,
        overall_score=overall_score,
        factor_scores=factor_scores,
        weights_used=weights_dict,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        match_explanation=" ".join(explanation_parts),
        recommended_preparation=prep_items,
    )
