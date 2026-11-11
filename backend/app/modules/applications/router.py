"""Application Tracking API v1 routes (/api/v1/applications/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep
from app.modules.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationSummaryResponse,
    ApplicationTransitionRequest,
    ApplicationUpdateRequest,
)
from app.modules.applications.service import ApplicationService
from app.modules.authentication.dependencies import CurrentUserDep

router = APIRouter(prefix="/applications", tags=["Applications"])


def get_application_service(session: DBSessionDep) -> ApplicationService:
    return ApplicationService(session=session)


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List tracked applications for the authenticated user",
)
async def list_applications(
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApplicationListResponse:
    return await service.list_applications(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary",
    response_model=ApplicationSummaryResponse,
    summary="Get application pipeline counts and upcoming deadlines",
)
async def get_application_summary(
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationSummaryResponse:
    return await service.get_summary(user_id=current_user.id)


@router.post(
    "",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tracked job application",
)
async def create_application(
    payload: ApplicationCreateRequest,
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationDetailResponse:
    return await service.create_application(user_id=current_user.id, payload=payload)


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get application details and status history",
)
async def get_application(
    application_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationDetailResponse:
    return await service.get_application(user_id=current_user.id, application_id=application_id)


@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Update application metadata, notes, links, or deadlines",
)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdateRequest,
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationDetailResponse:
    return await service.update_application(
        user_id=current_user.id,
        application_id=application_id,
        payload=payload,
    )


@router.post(
    "/{application_id}/transition",
    response_model=ApplicationDetailResponse,
    summary="Transition application status through validated state machine",
)
async def transition_application(
    application_id: uuid.UUID,
    payload: ApplicationTransitionRequest,
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationDetailResponse:
    return await service.transition_status(
        user_id=current_user.id,
        application_id=application_id,
        payload=payload,
    )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tracked application",
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> None:
    await service.delete_application(user_id=current_user.id, application_id=application_id)
