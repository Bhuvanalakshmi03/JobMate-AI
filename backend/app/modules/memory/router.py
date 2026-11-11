"""Consent-gated Career Memory API v1 routes (/api/v1/memory/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.memory.schemas import (
    CareerMemoryCreateRequest,
    CareerMemoryListResponse,
    CareerMemoryResponse,
    CareerMemoryUpdateRequest,
    MemoryConsentResponse,
    MemoryConsentUpdateRequest,
)
from app.modules.memory.service import CareerMemoryService

router = APIRouter(prefix="/memory", tags=["Career Memory & Consent"])


def get_memory_service(session: DBSessionDep) -> CareerMemoryService:
    return CareerMemoryService(session)


MemoryServiceDep = Annotated[CareerMemoryService, Depends(get_memory_service)]


@router.get(
    "/consent",
    response_model=MemoryConsentResponse,
    summary="Get user memory and notification consent settings",
)
async def get_memory_consent(
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> MemoryConsentResponse:
    return await service.get_consent(user=current_user)


@router.patch(
    "/consent",
    response_model=MemoryConsentResponse,
    summary="Update Career Memory and notification consent flags",
)
async def update_memory_consent(
    payload: MemoryConsentUpdateRequest,
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> MemoryConsentResponse:
    return await service.update_consent(user=current_user, payload=payload)


@router.get(
    "",
    response_model=CareerMemoryListResponse,
    summary="List Career Memory entries owned by the authenticated user",
)
async def list_memories(
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
    category: str | None = Query(default=None),
    approved_only: bool = Query(default=False),
) -> CareerMemoryListResponse:
    return await service.list_memories(
        user=current_user, category=category, approved_only=approved_only
    )


@router.post(
    "",
    response_model=CareerMemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a user-approved Career Memory entry (requires consent)",
)
async def create_memory(
    payload: CareerMemoryCreateRequest,
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> CareerMemoryResponse:
    return await service.create_memory(user=current_user, payload=payload)


@router.patch(
    "/{memory_id}",
    response_model=CareerMemoryResponse,
    summary="Edit, approve, or deactivate a Career Memory entry",
)
async def update_memory(
    memory_id: uuid.UUID,
    payload: CareerMemoryUpdateRequest,
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> CareerMemoryResponse:
    return await service.update_memory(
        user=current_user, memory_id=memory_id, payload=payload
    )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single Career Memory entry",
)
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> None:
    await service.delete_memory(user=current_user, memory_id=memory_id)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all Career Memory entries for the current user",
)
async def clear_all_memories(
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> None:
    await service.clear_memories(user=current_user)
