"""Multi-Agent & RAG API v1 routes (/api/v1/agents/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import DBSessionDep, SettingsDep
from app.modules.agents.schemas import (
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSyncResponse,
    WorkflowCreateRequest,
    WorkflowListResponse,
    WorkflowRunResponse,
)
from app.modules.agents.service import AgentOrchestrationService
from app.modules.authentication.dependencies import CurrentUserDep

router = APIRouter(prefix="/agents", tags=["Multi-Agent Co-Pilot"])


def get_agent_service(
    session: DBSessionDep,
    settings: SettingsDep,
) -> AgentOrchestrationService:
    return AgentOrchestrationService(session=session, settings=settings)


AgentServiceDep = Annotated[AgentOrchestrationService, Depends(get_agent_service)]


@router.post(
    "/workflows",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a JobMate AI LangGraph multi-agent workflow",
)
async def create_workflow(
    payload: WorkflowCreateRequest,
    current_user: CurrentUserDep,
    service: AgentServiceDep,
) -> WorkflowRunResponse:
    return await service.start_workflow(user=current_user, payload=payload)


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="List multi-agent workflow runs owned by the authenticated user",
)
async def list_workflows(
    current_user: CurrentUserDep,
    service: AgentServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkflowListResponse:
    return await service.list_workflows(user=current_user, limit=limit, offset=offset)


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowRunResponse,
    summary="Inspect multi-agent workflow state, outputs, and execution trace",
)
async def get_workflow(
    workflow_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: AgentServiceDep,
) -> WorkflowRunResponse:
    return await service.get_workflow(user=current_user, workflow_id=workflow_id)


@router.post(
    "/rag/sync",
    response_model=RAGSyncResponse,
    summary="Index user-verified career facts and documents into ChromaDB vector store",
)
async def sync_rag_index(
    current_user: CurrentUserDep,
    service: AgentServiceDep,
) -> RAGSyncResponse:
    return await service.sync_rag(user=current_user)


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    summary="Query user-isolated RAG career context",
)
async def query_rag_context(
    payload: RAGQueryRequest,
    current_user: CurrentUserDep,
    service: AgentServiceDep,
) -> RAGQueryResponse:
    return await service.query_rag(user=current_user, payload=payload)

