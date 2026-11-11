"""Database repository for Co-Pilot chat sessions and message turns."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.modules.copilot.models import CopilotConversation, CopilotMessage


class CopilotRepository:
    """User-scoped CRUD for CopilotConversation and CopilotMessage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(
        self,
        *,
        user_id: uuid.UUID,
        title: str = "New Co-Pilot Chat",
    ) -> CopilotConversation:
        now = utc_now()
        conv = CopilotConversation(
            user_id=user_id,
            title=title.strip()[:200] or "New Co-Pilot Chat",
            is_archived=False,
            last_message_at=now,
        )
        self._session.add(conv)
        await self._session.flush()
        await self._session.refresh(conv)
        return conv

    async def get_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CopilotConversation | None:
        return await self._session.scalar(
            select(CopilotConversation).where(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == user_id,
            )
        )

    async def list_conversations(
        self,
        *,
        user_id: uuid.UUID,
        include_archived: bool = False,
        limit: int = 50,
    ) -> tuple[list[CopilotConversation], int]:
        base = select(CopilotConversation).where(CopilotConversation.user_id == user_id)
        if not include_archived:
            base = base.where(CopilotConversation.is_archived.is_(False))
        total = int(
            await self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        rows = list(
            (
                await self._session.scalars(
                    base.order_by(CopilotConversation.last_message_at.desc()).limit(limit)
                )
            ).all()
        )
        return rows, total

    async def delete_conversation(self, conv: CopilotConversation) -> None:
        await self._session.delete(conv)
        await self._session.flush()

    async def add_message(
        self,
        *,
        conversation: CopilotConversation,
        user_id: uuid.UUID,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        approval_ids: list[str] | None = None,
        tokens_used: int = 0,
    ) -> CopilotMessage:
        msg = CopilotMessage(
            conversation_id=conversation.id,
            user_id=user_id,
            role=role,
            content=content,
            tool_calls=list(tool_calls or []),
            approval_ids=list(approval_ids or []),
            tokens_used=tokens_used,
        )
        conversation.last_message_at = utc_now()
        self._session.add(msg)
        await self._session.flush()
        await self._session.refresh(msg)
        return msg

    async def list_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[CopilotMessage]:
        stmt = (
            select(CopilotMessage)
            .where(
                CopilotMessage.conversation_id == conversation_id,
                CopilotMessage.user_id == user_id,
            )
            .order_by(CopilotMessage.created_at.asc())
            .limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())
