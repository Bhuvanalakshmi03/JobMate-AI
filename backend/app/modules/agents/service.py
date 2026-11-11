"""Orchestration service managing LangGraph workflow runs, pause/resume, and RAG ops."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_careerpilot_graph
from app.agents.state import (
    CareerPilotAgentState,
    create_initial_agent_state,
    serialize_state_snapshot,
)
from app.agents.tools.registry import AgentToolset
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.integrations.chroma.store import VectorStoreProtocol, create_vector_store
from app.integrations.job_search.openai_web_search import (
    JobSearchProviderProtocol,
    OpenAIWebSearchJobProvider,
)
from app.integrations.openai.client import (
    EmbeddingClientProtocol,
    LLMClientProtocol,
    OpenAIChatClient,
)
from app.modules.agents.repository import WorkflowRunRepository
from app.modules.agents.schemas import (
    RAGHitResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSyncResponse,
    WorkflowCreateRequest,
    WorkflowListResponse,
    WorkflowRunResponse,
)
from app.modules.applications.repository import ApplicationRepository
from app.modules.approvals.models import ApprovalRequest
from app.modules.authentication.models import User
from app.modules.documents.generator import DocumentGeneratorProtocol, OpenAIDocumentGenerator
from app.modules.jobs.repository import JobRepository
from app.modules.rag.service import RAGService
from app.modules.resume.repository import ResumeRepository
from app.repositories.audit_repository import AuditLogRepository


class AgentOrchestrationService:
    """Coordinates LangGraph multi-agent workflows, durable checkpoints, and RAG indexing."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        llm_client: LLMClientProtocol | None = None,
        embedding_client: EmbeddingClientProtocol | None = None,
        vector_store: VectorStoreProtocol | None = None,
        job_search_provider: JobSearchProviderProtocol | None = None,
        document_generator: DocumentGeneratorProtocol | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        default_ai = OpenAIChatClient(settings)
        self._llm: LLMClientProtocol = llm_client or default_ai
        self._embeddings: EmbeddingClientProtocol = embedding_client or default_ai
        self._vectors: VectorStoreProtocol = vector_store or create_vector_store(settings)
        self._job_provider: JobSearchProviderProtocol = (
            job_search_provider or OpenAIWebSearchJobProvider(default_ai)
        )
        self._doc_generator: DocumentGeneratorProtocol = (
            document_generator or OpenAIDocumentGenerator(self._llm)
        )

        self._runs = WorkflowRunRepository(session)
        self._jobs = JobRepository(session)
        self._resumes = ResumeRepository(session)
        self._apps = ApplicationRepository(session)
        self._audit = AuditLogRepository(session)

    def _build_toolset(self, user: User) -> AgentToolset:
        return AgentToolset(
            session=self._session,
            settings=self._settings,
            user=user,
            llm_client=self._llm,
            embedding_client=self._embeddings,
            vector_store=self._vectors,
            job_search_provider=self._job_provider,
            document_generator=self._doc_generator,
        )

    async def start_workflow(
        self,
        *,
        user: User,
        payload: WorkflowCreateRequest,
    ) -> WorkflowRunResponse:
        if payload.job_id is not None:
            job = await self._jobs.get_by_id(payload.job_id)
            if job is None:
                raise NotFoundError("Target job listing not found.")
        if payload.resume_id is not None:
            resume = await self._resumes.get_by_id_for_user(
                resume_id=payload.resume_id, user_id=user.id
            )
            if resume is None:
                raise NotFoundError("Source resume not found.")
        if payload.application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=payload.application_id, user_id=user.id
            )
            if app is None:
                raise NotFoundError("Application not found.")

        record = await self._runs.create(
            user_id=user.id,
            task_type=payload.task_type,
            user_request=payload.requested_task.strip(),
            job_id=payload.job_id,
            application_id=payload.application_id,
        )

        initial_state = create_initial_agent_state(
            user_id=str(user.id),
            workflow_id=str(record.id),
            requested_task=payload.requested_task.strip(),
            requested_task_type=payload.task_type,
            job_id=str(payload.job_id) if payload.job_id else None,
            resume_id=str(payload.resume_id) if payload.resume_id else None,
            application_id=str(payload.application_id) if payload.application_id else None,
            search_query=payload.search_query,
            search_location=payload.search_location,
        )

        toolset = self._build_toolset(user)
        graph = build_careerpilot_graph(toolset=toolset)
        final_state = cast(
            dict[str, Any],
            await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": str(record.id)}},
            ),
        )
        updated = await self._runs.apply_state(
            record,
            state=serialize_state_snapshot(cast(CareerPilotAgentState, final_state)),
        )

        await self._audit.record(
            event_type="agent.workflow_started",
            user_id=user.id,
            resource_type="workflow_run",
            resource_id=str(updated.id),
            details={
                "task_type": updated.task_type,
                "status": updated.status,
                "current_stage": updated.current_stage,
                "tokens_used": updated.total_tokens_used,
            },
        )
        return WorkflowRunResponse.model_validate(updated)

    async def resume_from_approval(
        self,
        *,
        approval: ApprovalRequest,
        decision: str,
    ) -> WorkflowRunResponse | None:
        if approval.workflow_run_id is None:
            return None

        record = await self._runs.get_by_id_for_user(
            workflow_id=approval.workflow_run_id,
            user_id=approval.user_id,
        )
        if record is None:
            return None

        user = await self._session.scalar(select(User).where(User.id == approval.user_id))
        if user is None:
            return None

        hydrated_state = dict(record.state_snapshot or {})
        if not hydrated_state:
            hydrated_state = dict(
                create_initial_agent_state(
                    user_id=str(user.id),
                    workflow_id=str(record.id),
                    requested_task=record.user_request,
                    requested_task_type=record.task_type,
                )
            )
        hydrated_state["pending_approval_id"] = str(approval.id)
        hydrated_state["approval_decision"] = decision
        hydrated_state["application_id"] = (
            str(approval.application_id)
            if approval.application_id
            else hydrated_state.get("application_id")
        )

        toolset = self._build_toolset(user)
        graph = build_careerpilot_graph(toolset=toolset)
        resumed_state = cast(
            dict[str, Any],
            await graph.ainvoke(
                hydrated_state,
                config={"configurable": {"thread_id": str(record.id)}},
            ),
        )
        updated = await self._runs.apply_state(
            record,
            state=serialize_state_snapshot(cast(CareerPilotAgentState, resumed_state)),
        )
        return WorkflowRunResponse.model_validate(updated)

    async def list_workflows(
        self,
        *,
        user: User,
        limit: int = 30,
        offset: int = 0,
    ) -> WorkflowListResponse:
        rows, total = await self._runs.list_for_user(user_id=user.id, limit=limit, offset=offset)
        return WorkflowListResponse(
            items=[WorkflowRunResponse.model_validate(r) for r in rows],
            total=total,
        )

    async def get_workflow(
        self,
        *,
        user: User,
        workflow_id: uuid.UUID,
    ) -> WorkflowRunResponse:
        record = await self._runs.get_by_id_for_user(workflow_id=workflow_id, user_id=user.id)
        if record is None:
            raise NotFoundError("Workflow run not found.")
        return WorkflowRunResponse.model_validate(record)

    async def sync_rag(self, *, user: User) -> RAGSyncResponse:
        rag = RAGService(
            session=self._session,
            settings=self._settings,
            vector_store=self._vectors,
            embedding_client=self._embeddings,
        )
        result = await rag.index_user_career_context(user_id=user.id)
        await self._audit.record(
            event_type="rag.indexed",
            user_id=user.id,
            resource_type="rag_index",
            resource_id=str(user.id),
            details={
                "indexed_chunks": result.indexed_chunks,
                "skipped_duplicates": result.skipped_duplicates,
            },
        )
        return RAGSyncResponse(
            indexed_chunks=result.indexed_chunks,
            skipped_duplicates=result.skipped_duplicates,
            source_counts=result.source_counts,
        )

    async def query_rag(self, *, user: User, payload: RAGQueryRequest) -> RAGQueryResponse:
        rag = RAGService(
            session=self._session,
            settings=self._settings,
            vector_store=self._vectors,
            embedding_client=self._embeddings,
        )
        hits = await rag.retrieve_context(
            user_id=user.id,
            query=payload.query,
            top_k=payload.top_k,
            source_types=payload.source_types,
        )
        return RAGQueryResponse(
            query=payload.query,
            hits=[
                RAGHitResponse(
                    chunk_id=h.chunk_id,
                    score=h.score,
                    source_type=(
                        str(h.metadata["source_type"]) if h.metadata.get("source_type") else None
                    ),
                    label=str(h.metadata["label"]) if h.metadata.get("label") else None,
                    text=h.text,
                )
                for h in hits
            ],
        )
