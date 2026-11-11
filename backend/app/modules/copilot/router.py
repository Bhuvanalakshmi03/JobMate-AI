"""Session-managed Co-Pilot Chat API v1 routes (/api/v1/copilot/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import DBSessionDep, SettingsDep
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.copilot.schemas import (
    ChatTurnResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    MessageSendRequest,
)
from app.modules.copilot.service import CopilotChatService

router = APIRouter(prefix="/copilot", tags=["Co-Pilot Chat"])


def get_copilot_chat_service(
    session: DBSessionDep,
    settings: SettingsDep,
) -> CopilotChatService:
    return CopilotChatService(session=session, settings=settings)


CopilotChatServiceDep = Annotated[CopilotChatService, Depends(get_copilot_chat_service)]


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List persistent Co-Pilot chat conversation sessions",
)
async def list_conversations(
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
) -> ConversationListResponse:
    return await service.list_conversations(user=current_user)


@router.post(
    "/conversations",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Co-Pilot chat session",
)
async def create_conversation(
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
    payload: ConversationCreateRequest | None = None,
) -> ConversationSummary:
    return await service.create_conversation(
        user=current_user,
        payload=payload or ConversationCreateRequest(),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Load full message history and linked approvals for a chat session",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
) -> ConversationDetailResponse:
    return await service.get_conversation(user=current_user, conversation_id=conversation_id)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="Rename or archive a Co-Pilot chat session",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdateRequest,
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
) -> ConversationSummary:
    return await service.update_conversation(
        user=current_user,
        conversation_id=conversation_id,
        payload=payload,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Co-Pilot chat session",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
) -> None:
    await service.delete_conversation(user=current_user, conversation_id=conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatTurnResponse,
    summary="Send a message in a Co-Pilot chat session and execute OpenAI tool calls",
)
async def send_chat_message(
    conversation_id: uuid.UUID,
    payload: MessageSendRequest,
    current_user: CurrentUserDep,
    service: CopilotChatServiceDep,
) -> ChatTurnResponse:
    return await service.send_message(
        user=current_user,
        conversation_id=conversation_id,
        payload=payload,
    )
