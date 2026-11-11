"""Pydantic schemas for mock interview preparation, evaluation, and skill improvement."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InterviewFocusArea = Literal["mixed", "technical", "behavioral", "hr"]
InterviewDifficulty = Literal["entry", "intermediate", "senior"]
InterviewCategory = Literal["technical", "behavioral", "hr", "role_specific"]
InterviewSessionStatus = Literal["CREATED", "IN_PROGRESS", "EVALUATED"]


class InterviewSessionCreateRequest(BaseModel):
    """Create a tailored mock interview preparation session."""

    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    focus_area: InterviewFocusArea = "mixed"
    difficulty: InterviewDifficulty = "entry"
    question_count: int = Field(default=5, ge=1, le=12)
    generate_questions: bool = True


class GenerateQuestionsRequest(BaseModel):
    """Request to generate additional targeted interview questions for a session."""

    count: int = Field(default=5, ge=1, le=12)
    focus_area: InterviewFocusArea | None = None


class SubmitAnswerRequest(BaseModel):
    """Submit or revise a candidate answer for an interview question."""

    question_id: uuid.UUID
    answer_text: str = Field(min_length=5, max_length=8000)
    time_spent_seconds: int | None = Field(default=None, ge=1, le=7200)


class RubricBreakdown(BaseModel):
    """Documented four-criterion interview rubric (0..100 each)."""

    technical_accuracy: float = Field(ge=0.0, le=100.0)
    communication_clarity: float = Field(ge=0.0, le=100.0)
    star_structure: float = Field(ge=0.0, le=100.0)
    role_alignment: float = Field(ge=0.0, le=100.0)


class QuestionEvaluationItem(BaseModel):
    """Structured rubric evaluation for an individual question and answer."""

    question_id: str
    prompt: str = ""
    category: str = "technical"
    score: float = Field(ge=0.0, le=100.0)
    rubric: RubricBreakdown
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    sample_strong_points: list[str] = Field(default_factory=list)


class SkillImprovementItem(BaseModel):
    """Prioritized actionable recommendation to close an identified skill gap."""

    skill: str
    current_gap: str
    priority: Literal["high", "medium", "low"] = "medium"
    action_items: list[str] = Field(default_factory=list)
    estimated_hours: int = Field(default=4, ge=1, le=200)


class InterviewQuestionResponse(BaseModel):
    """Serialized interview question."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    order_index: int
    category: str
    prompt: str
    expected_topics: list[str]
    difficulty: str
    guidance: str | None
    created_at: datetime


class InterviewAnswerResponse(BaseModel):
    """Serialized candidate answer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    session_id: uuid.UUID
    answer_text: str
    time_spent_seconds: int | None
    submitted_at: datetime


class InterviewFeedbackResponse(BaseModel):
    """Serialized evaluation feedback and skill improvement plan."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    overall_score: float
    rubric_scores: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]
    question_evaluations: list[QuestionEvaluationItem]
    skill_improvement_plan: list[SkillImprovementItem]
    summary: str
    model_used: str | None
    tokens_used: int
    evaluated_at: datetime


class InterviewSessionSummary(BaseModel):
    """Summary card representation of a mock interview session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID | None
    application_id: uuid.UUID | None
    title: str
    target_role: str
    company_name: str | None
    focus_area: str
    difficulty: str
    status: str
    question_count: int
    overall_score: float | None
    created_at: datetime
    updated_at: datetime


class InterviewSessionDetailResponse(BaseModel):
    """Full mock interview workspace state: session, questions, answers, feedback."""

    session: InterviewSessionSummary
    questions: list[InterviewQuestionResponse]
    answers: list[InterviewAnswerResponse]
    feedback: InterviewFeedbackResponse | None = None


class InterviewSessionListResponse(BaseModel):
    """Paginated list of user mock interview sessions."""

    items: list[InterviewSessionSummary]
    total: int


class SkillGapPlanResponse(BaseModel):
    """Consolidated cross-job and interview skill gap analysis and improvement roadmap."""

    verified_skills: list[str]
    missing_skills_from_matches: list[str]
    recurring_interview_weaknesses: list[str]
    average_interview_score: float | None
    evaluated_sessions_count: int
    improvement_plan: list[SkillImprovementItem]
