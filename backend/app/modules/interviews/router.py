"""Mock interview preparation, evaluation, and skill-gap API v1 routes (/api/v1/interviews/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep, SettingsDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.interviews.schemas import (
    GenerateQuestionsRequest,
    InterviewAnswerResponse,
    InterviewFeedbackResponse,
    InterviewQuestionResponse,
    InterviewSessionCreateRequest,
    InterviewSessionDetailResponse,
    InterviewSessionListResponse,
    SkillGapPlanResponse,
    SubmitAnswerRequest,
)
from app.modules.interviews.service import InterviewService

router = APIRouter(prefix="/interviews", tags=["Interview Preparation"])


def get_interview_service(
    session: DBSessionDep,
    settings: SettingsDep,
) -> InterviewService:
    return InterviewService(session=session, settings=settings)


InterviewServiceDep = Annotated[InterviewService, Depends(get_interview_service)]


@router.get(
    "/skill-gap-plan",
    response_model=SkillGapPlanResponse,
    summary="Get consolidated job-match & interview skill improvement roadmap",
)
async def get_skill_gap_plan(
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> SkillGapPlanResponse:
    return await service.get_skill_gap_plan(user=current_user)


@router.post(
    "",
    response_model=InterviewSessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mock interview session and optionally generate starter questions",
)
async def create_interview_session(
    payload: InterviewSessionCreateRequest,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> InterviewSessionDetailResponse:
    return await service.create_session(user=current_user, payload=payload)


@router.get(
    "",
    response_model=InterviewSessionListResponse,
    summary="List mock interview sessions owned by the current user",
)
async def list_interview_sessions(
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InterviewSessionListResponse:
    return await service.list_sessions(
        user=current_user, status=status_filter, limit=limit, offset=offset
    )


@router.get(
    "/{session_id}",
    response_model=InterviewSessionDetailResponse,
    summary="Get full interview session details, questions, answers, and feedback",
)
async def get_interview_session(
    session_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> InterviewSessionDetailResponse:
    return await service.get_session_detail(user=current_user, session_id=session_id)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a mock interview session",
)
async def delete_interview_session(
    session_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> None:
    await service.delete_session(user=current_user, session_id=session_id)


@router.post(
    "/{session_id}/questions",
    response_model=list[InterviewQuestionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate additional targeted questions for an interview session",
)
async def generate_interview_questions(
    session_id: uuid.UUID,
    payload: GenerateQuestionsRequest,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> list[InterviewQuestionResponse]:
    return await service.generate_more_questions(
        user=current_user, session_id=session_id, payload=payload
    )


@router.post(
    "/{session_id}/answers",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit or update a candidate answer in an interview session",
)
async def submit_interview_answer(
    session_id: uuid.UUID,
    payload: SubmitAnswerRequest,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> InterviewAnswerResponse:
    return await service.submit_answer(
        user=current_user, session_id=session_id, payload=payload
    )


@router.post(
    "/{session_id}/evaluate",
    response_model=InterviewFeedbackResponse,
    summary="Evaluate submitted answers using the documented interview rubric",
)
async def evaluate_interview_session(
    session_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> InterviewFeedbackResponse:
    return await service.evaluate_session(user=current_user, session_id=session_id)


@router.get(
    "/{session_id}/feedback",
    response_model=InterviewFeedbackResponse,
    summary="Retrieve persisted evaluation feedback for an interview session",
)
async def get_interview_feedback(
    session_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: InterviewServiceDep,
) -> InterviewFeedbackResponse:
    return await service.get_feedback(user=current_user, session_id=session_id)
