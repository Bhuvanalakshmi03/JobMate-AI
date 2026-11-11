"""Conversational Co-Pilot orchestration service managing chat sessions and tool calls."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.integrations.chroma.store import VectorStoreProtocol, create_vector_store
from app.integrations.job_search.openai_web_search import (
    JobSearchProviderProtocol,
    OpenAIWebSearchJobProvider,
)
from app.integrations.openai.client import (
    EmbeddingClientProtocol,
    OpenAIChatClient,
    ToolCallingClientProtocol,
)
from app.modules.approvals.models import ApprovalRequest
from app.modules.approvals.schemas import ApprovalResponse
from app.modules.authentication.models import User
from app.modules.calendar.service import CalendarService
from app.modules.copilot.repository import CopilotRepository
from app.modules.copilot.schemas import (
    ChatMessageResponse,
    ChatTurnResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    MessageSendRequest,
)
from app.modules.copilot.toolkit import COPILOT_TOOL_SCHEMAS, CopilotChatToolkit
from app.modules.documents.generator import DocumentGeneratorProtocol, OpenAIDocumentGenerator
from app.repositories.audit_repository import AuditLogRepository

COPILOT_SYSTEM_PROMPT = """You are JobMate AI Co-Pilot, an intelligent placement & career guide.
You have tools to manage the user's career profile, discover live jobs, calculate match
scores, generate tailored resumes and cover letters strictly from verified facts, track
applications, sync/query ChromaDB RAG knowledge, inspect approvals, and manage Google Calendar.

STRICT RULES:
1. NEVER invent qualifications, resume facts, jobs, URLs, or calendar events. Rely on tool outputs.
2. External actions (submitting a job application or adding a Google Calendar event) MUST go
   through `prepare_application_submission` or `propose_calendar_event` so the user gets a
   confirmation button. Never claim an external action is completed until the user approves it.
3. For relative dates ("tomorrow 10am"), compute explicit ISO-8601 timestamps in user timezone.
4. Keep responses concise, structured, and actionable. Reference IDs or links returned cleanly.
"""


def _derive_conversation_title(first_message: str) -> str:
    cleaned = " ".join(first_message.strip().split())
    if len(cleaned) <= 72:
        return cleaned or "New Co-Pilot Chat"
    return cleaned[:69].rstrip() + "..."


class CopilotChatService:
    """Manages persistent multi-turn chat sessions and OpenAI tool calling."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        tool_client: ToolCallingClientProtocol | None = None,
        embedding_client: EmbeddingClientProtocol | None = None,
        vector_store: VectorStoreProtocol | None = None,
        job_search_provider: JobSearchProviderProtocol | None = None,
        document_generator: DocumentGeneratorProtocol | None = None,
        calendar_service: CalendarService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        default_ai = OpenAIChatClient(settings)
        self._tool_client: ToolCallingClientProtocol = tool_client or default_ai
        self._embeddings: EmbeddingClientProtocol = embedding_client or default_ai
        self._vectors: VectorStoreProtocol = vector_store or create_vector_store(settings)
        self._job_provider: JobSearchProviderProtocol = (
            job_search_provider or OpenAIWebSearchJobProvider(default_ai)
        )
        self._doc_generator: DocumentGeneratorProtocol = (
            document_generator or OpenAIDocumentGenerator(default_ai)
        )
        self._calendar = calendar_service or CalendarService(session=session, settings=settings)
        self._repo = CopilotRepository(session)
        self._audit = AuditLogRepository(session)

    async def create_conversation(
        self,
        *,
        user: User,
        payload: ConversationCreateRequest,
    ) -> ConversationSummary:
        conv = await self._repo.create_conversation(
            user_id=user.id,
            title=payload.title or "New Co-Pilot Chat",
        )
        return ConversationSummary.model_validate(conv)

    async def list_conversations(self, *, user: User) -> ConversationListResponse:
        rows, total = await self._repo.list_conversations(user_id=user.id)
        return ConversationListResponse(
            items=[ConversationSummary.model_validate(r) for r in rows],
            total=total,
        )

    async def _load_approvals_by_ids(
        self,
        *,
        user_id: uuid.UUID,
        raw_ids: list[str],
    ) -> list[ApprovalResponse]:
        parsed: list[uuid.UUID] = []
        for raw in raw_ids:
            try:
                parsed.append(uuid.UUID(raw))
            except ValueError:
                continue
        if not parsed:
            return []
        rows = list(
            (
                await self._session.scalars(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.user_id == user_id, ApprovalRequest.id.in_(parsed))
                    .order_by(ApprovalRequest.created_at.desc())
                )
            ).all()
        )
        return [ApprovalResponse.model_validate(row) for row in rows]

    async def get_conversation(
        self,
        *,
        user: User,
        conversation_id: uuid.UUID,
    ) -> ConversationDetailResponse:
        conv = await self._repo.get_conversation(conversation_id=conversation_id, user_id=user.id)
        if conv is None:
            raise NotFoundError("Co-Pilot conversation not found.")
        msgs = await self._repo.list_messages(conversation_id=conv.id, user_id=user.id)
        all_approval_ids = [aid for m in msgs for aid in (m.approval_ids or [])]
        approvals = await self._load_approvals_by_ids(user_id=user.id, raw_ids=all_approval_ids)
        return ConversationDetailResponse(
            conversation=ConversationSummary.model_validate(conv),
            messages=[ChatMessageResponse.model_validate(m) for m in msgs],
            approvals=approvals,
        )

    async def update_conversation(
        self,
        *,
        user: User,
        conversation_id: uuid.UUID,
        payload: ConversationUpdateRequest,
    ) -> ConversationSummary:
        conv = await self._repo.get_conversation(conversation_id=conversation_id, user_id=user.id)
        if conv is None:
            raise NotFoundError("Co-Pilot conversation not found.")
        if payload.title is not None:
            conv.title = payload.title.strip()[:200] or conv.title
        if payload.is_archived is not None:
            conv.is_archived = payload.is_archived
        await self._session.flush()
        await self._session.refresh(conv)
        return ConversationSummary.model_validate(conv)

    async def delete_conversation(
        self,
        *,
        user: User,
        conversation_id: uuid.UUID,
    ) -> None:
        conv = await self._repo.get_conversation(conversation_id=conversation_id, user_id=user.id)
        if conv is None:
            raise NotFoundError("Co-Pilot conversation not found.")
        await self._repo.delete_conversation(conv)

    async def send_message(
        self,
        *,
        user: User,
        conversation_id: uuid.UUID,
        payload: MessageSendRequest,
    ) -> ChatTurnResponse:
        conv = await self._repo.get_conversation(conversation_id=conversation_id, user_id=user.id)
        if conv is None:
            raise NotFoundError("Co-Pilot conversation not found.")

        prior_messages = await self._repo.list_messages(
            conversation_id=conv.id, user_id=user.id, limit=24
        )
        if not prior_messages and conv.title == "New Co-Pilot Chat":
            conv.title = _derive_conversation_title(payload.message)

        user_msg = await self._repo.add_message(
            conversation=conv,
            user_id=user.id,
            role="user",
            content=payload.message.strip(),
        )

        cal_status = await self._calendar.get_status(user_id=user.id)
        system_context = (
            f"{COPILOT_SYSTEM_PROMPT}\n"
            f"Current UTC time: {datetime.now(UTC).isoformat()}\n"
            f"User name: {user.full_name} | Timezone: {user.timezone}\n"
            f"Google Calendar connected: {cal_status.connected} "
            f"({cal_status.google_email or 'not connected'})"
        )
        llm_messages: list[dict[str, Any]] = [{"role": "system", "content": system_context}]
        for item in prior_messages[-20:]:
            llm_messages.append({"role": item.role, "content": item.content})
        llm_messages.append({"role": "user", "content": user_msg.content})

        toolkit = CopilotChatToolkit(
            session=self._session,
            settings=self._settings,
            user=user,
            embedding_client=self._embeddings,
            vector_store=self._vectors,
            job_search_provider=self._job_provider,
            document_generator=self._doc_generator,
            calendar_service=self._calendar,
        )

        result = await self._tool_client.complete_with_tools(
            messages=llm_messages,
            tools=COPILOT_TOOL_SCHEMAS,
            tool_executor=toolkit.execute,
            max_rounds=6,
        )

        assistant_msg = await self._repo.add_message(
            conversation=conv,
            user_id=user.id,
            role="assistant",
            content=result.content,
            tool_calls=list(result.executed_tools),
            approval_ids=list(toolkit.created_approval_ids),
            tokens_used=result.total_tokens,
        )
        await self._session.flush()
        await self._session.refresh(conv)

        created_approvals = await self._load_approvals_by_ids(
            user_id=user.id,
            raw_ids=toolkit.created_approval_ids,
        )
        await self._audit.record(
            event_type="copilot.turn_completed",
            user_id=user.id,
            resource_type="copilot_conversation",
            resource_id=str(conv.id),
            details={
                "tools_executed": [t.get("tool_name") for t in result.executed_tools],
                "tokens_used": result.total_tokens,
                "created_approvals": len(created_approvals),
            },
        )
        return ChatTurnResponse(
            conversation=ConversationSummary.model_validate(conv),
            user_message=ChatMessageResponse.model_validate(user_msg),
            assistant_message=ChatMessageResponse.model_validate(assistant_msg),
            created_approvals=created_approvals,
        )
