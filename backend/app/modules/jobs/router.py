"""Job discovery, matching, and bookmarking API v1 routes (/api/v1/jobs/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.core.dependencies import DBSessionDep, SettingsDep
from app.integrations.job_search.openai_web_search import JobSearchProviderProtocol
from app.integrations.llm.factory import create_embedding_client, create_job_search_provider
from app.integrations.openai.client import EmbeddingClientProtocol
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.jobs.schemas import (
    JobDetailResponse,
    JobSearchResponse,
    SavedJobResponse,
    SaveJobRequest,
)
from app.modules.jobs.service import JobDiscoveryService
from app.modules.matching.schemas import JobMatchResponse, RecommendedJobsResponse
from app.modules.matching.service import JobMatchingService

router = APIRouter(prefix="/jobs", tags=["Jobs & Matching"])


def get_job_search_provider(settings: SettingsDep) -> JobSearchProviderProtocol:
    """Provide live Web Search job discovery adapter for the configured LLM_MODE."""
    return create_job_search_provider(settings)


def get_embedding_client(settings: SettingsDep) -> EmbeddingClientProtocol | None:
    """Provide dense embedding client when OpenAI embeddings are configured."""
    return create_embedding_client(settings)


def get_job_discovery_service(
    session: DBSessionDep,
    settings: SettingsDep,
    provider: Annotated[JobSearchProviderProtocol, Depends(get_job_search_provider)],
) -> JobDiscoveryService:
    return JobDiscoveryService(session=session, settings=settings, search_provider=provider)


def get_job_matching_service(
    session: DBSessionDep,
    embedding_client: Annotated[EmbeddingClientProtocol | None, Depends(get_embedding_client)],
) -> JobMatchingService:
    return JobMatchingService(session=session, embedding_client=embedding_client)


JobDiscoveryServiceDep = Annotated[JobDiscoveryService, Depends(get_job_discovery_service)]
JobMatchingServiceDep = Annotated[JobMatchingService, Depends(get_job_matching_service)]


@router.get(
    "/search",
    response_model=JobSearchResponse,
    summary="Discover and filter live or persisted jobs",
)
async def search_jobs(
    current_user: CurrentUserDep,
    service: JobDiscoveryServiceDep,
    q: str | None = Query(default=None, max_length=200),
    location: str | None = Query(default=None, max_length=120),
    work_mode: str | None = Query(default=None, max_length=32),
    experience_level: str | None = Query(default=None, max_length=50),
    skills: str | None = Query(default=None, max_length=300),
    refresh: bool = Query(default=False),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> JobSearchResponse:
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    return await service.search_jobs(
        user=current_user,
        q=q,
        location=location,
        work_mode=work_mode,
        experience_level=experience_level,
        skills=skill_list,
        refresh=refresh,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/recommended",
    response_model=RecommendedJobsResponse,
    summary="Rank active jobs using explainable weighted and semantic matching",
)
async def get_recommended_jobs(
    current_user: CurrentUserDep,
    service: JobMatchingServiceDep,
    limit: int = Query(default=20, ge=1, le=50),
    use_semantic: bool = Query(default=True),
) -> RecommendedJobsResponse:
    return await service.get_recommended_jobs(
        user=current_user,
        limit=limit,
        use_semantic=use_semantic,
    )


@router.get(
    "/saved",
    response_model=JobSearchResponse,
    summary="List jobs saved by the authenticated user",
)
async def list_saved_jobs(
    current_user: CurrentUserDep,
    service: JobDiscoveryServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobSearchResponse:
    return await service.list_saved_jobs(user=current_user, limit=limit, offset=offset)


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get normalized job details",
)
async def get_job_details(
    job_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: JobDiscoveryServiceDep,
) -> JobDetailResponse:
    return await service.get_job_detail(user=current_user, job_id=job_id)


@router.post(
    "/{job_id}/match",
    response_model=JobMatchResponse,
    summary="Compute and persist explainable match score for a job",
)
async def calculate_job_match(
    job_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: JobMatchingServiceDep,
    use_semantic: bool = Query(default=True),
) -> JobMatchResponse:
    return await service.calculate_match_for_job(
        user=current_user,
        job_id=job_id,
        use_semantic=use_semantic,
    )


@router.post(
    "/{job_id}/save",
    response_model=SavedJobResponse,
    summary="Save a job listing to the authenticated user's shortlist",
)
async def save_job(
    job_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: JobDiscoveryServiceDep,
    payload: Annotated[SaveJobRequest | None, Body()] = None,
) -> SavedJobResponse:
    return await service.save_job(
        user=current_user,
        job_id=job_id,
        notes=payload.notes if payload else None,
    )


@router.delete(
    "/{job_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a job from the authenticated user's saved list",
)
async def unsave_job(
    job_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: JobDiscoveryServiceDep,
) -> None:
    await service.unsave_job(user=current_user, job_id=job_id)
