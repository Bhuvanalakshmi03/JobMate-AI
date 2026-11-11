"""Human Approval API v1 routes (/api/v1/approvals/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep
from app.modules.agents.router import AgentServiceDep
from app.modules.approvals.models import ApprovalRequest
from app.modules.approvals.schemas import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)
from app.modules.approvals.service import ApprovalService
from app.modules.authentication.dependencies import CurrentUserDep

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def get_approval_service(
    session: DBSessionDep,
    orchestrator: AgentServiceDep,
) -> ApprovalService:
    async def _on_decision(approval: ApprovalRequest, decision: str) -> None:
        await orchestrator.resume_from_approval(approval=approval, decision=decision)

    return ApprovalService(session=session, workflow_hook=_on_decision)


ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


@router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List human approval requests for the authenticated user",
)
async def list_approvals(
    current_user: CurrentUserDep,
    service: ApprovalServiceDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApprovalListResponse:
    return await service.list_approvals(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare a human-approval request for an external action",
)
async def create_approval(
    payload: ApprovalCreateRequest,
    current_user: CurrentUserDep,
    service: ApprovalServiceDep,
) -> ApprovalResponse:
    return await service.create_approval(user_id=current_user.id, payload=payload)


@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    summary="Inspect prepared action payload and approval decision status",
)
async def get_approval(
    approval_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ApprovalServiceDep,
) -> ApprovalResponse:
    return await service.get_approval(user_id=current_user.id, approval_id=approval_id)


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalResponse,
    summary="Explicitly approve and execute a pending external action",
)
async def approve_action(
    approval_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ApprovalServiceDep,
    payload: ApprovalDecisionRequest | None = None,
) -> ApprovalResponse:
    return await service.approve(
        user_id=current_user.id,
        approval_id=approval_id,
        decision=payload or ApprovalDecisionRequest(),
    )


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject a pending external action and prevent execution",
)
async def reject_action(
    approval_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ApprovalServiceDep,
    payload: ApprovalDecisionRequest | None = None,
) -> ApprovalResponse:
    return await service.reject(
        user_id=current_user.id,
        approval_id=approval_id,
        decision=payload or ApprovalDecisionRequest(),
    )
