"""Profile and skills API v1 routes (/api/v1/profile/*)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import DBSessionDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.profile.schemas import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    SkillsListResponse,
    SkillsUpdateRequest,
)
from app.modules.profile.service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


def get_profile_service(session: DBSessionDep) -> ProfileService:
    """Build request-scoped ProfileService."""
    return ProfileService(session=session)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Get authenticated user's career profile",
)
async def get_profile(
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> ProfileResponse:
    return await service.get_profile(user=current_user)


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create career profile for authenticated user",
)
async def create_profile(
    payload: ProfileCreateRequest,
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> ProfileResponse:
    return await service.create_profile(user=current_user, payload=payload)


@router.put(
    "",
    response_model=ProfileResponse,
    summary="Create or update authenticated user's career profile",
)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> ProfileResponse:
    return await service.update_profile(user=current_user, payload=payload)


@router.get(
    "/skills",
    response_model=SkillsListResponse,
    summary="List authenticated user's skills",
)
async def get_skills(
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> SkillsListResponse:
    return await service.get_skills(user=current_user)


@router.put(
    "/skills",
    response_model=SkillsListResponse,
    summary="Replace authenticated user's skills",
)
async def update_skills(
    payload: SkillsUpdateRequest,
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> SkillsListResponse:
    return await service.replace_skills(user=current_user, payload=payload)

