"""Domain service enforcing explicit privacy consent and ownership on Career Memory."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.authentication.models import User
from app.modules.memory.repository import CareerMemoryRepository
from app.modules.memory.schemas import (
    CareerMemoryCreateRequest,
    CareerMemoryListResponse,
    CareerMemoryResponse,
    CareerMemoryUpdateRequest,
    MemoryConsentResponse,
    MemoryConsentUpdateRequest,
)
from app.modules.profile.models import UserProfile
from app.modules.profile.repository import ProfileRepository
from app.repositories.audit_repository import AuditLogRepository


class CareerMemoryService:
    """User-controlled Career Memory CRUD guarded by explicit privacy consent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CareerMemoryRepository(session)
        self._profiles = ProfileRepository(session)
        self._audit = AuditLogRepository(session)

    async def _get_or_init_profile(self, user: User) -> UserProfile:
        profile = await self._profiles.get_by_user_id(user.id)
        if profile is None:
            profile = UserProfile(user_id=user.id)
            self._session.add(profile)
            await self._session.flush()
            await self._session.refresh(profile)
        return profile

    async def get_consent(self, *, user: User) -> MemoryConsentResponse:
        profile = await self._profiles.get_by_user_id(user.id)
        if profile is None:
            return MemoryConsentResponse(ai_consent_given=False, notification_consent=False)
        return MemoryConsentResponse(
            ai_consent_given=profile.ai_consent_given,
            notification_consent=profile.notification_consent,
        )

    async def update_consent(
        self, *, user: User, payload: MemoryConsentUpdateRequest
    ) -> MemoryConsentResponse:
        profile = await self._get_or_init_profile(user)
        profile.ai_consent_given = payload.ai_consent_given
        if payload.notification_consent is not None:
            profile.notification_consent = payload.notification_consent
        await self._session.flush()
        await self._audit.record(
            event_type="memory.consent_updated",
            user_id=user.id,
            resource_type="user_profile",
            resource_id=str(profile.id),
            details={
                "ai_consent_given": profile.ai_consent_given,
                "notification_consent": profile.notification_consent,
            },
        )
        return MemoryConsentResponse(
            ai_consent_given=profile.ai_consent_given,
            notification_consent=profile.notification_consent,
        )

    async def list_memories(
        self,
        *,
        user: User,
        category: str | None = None,
        approved_only: bool = False,
    ) -> CareerMemoryListResponse:
        consent = await self.get_consent(user=user)
        rows, total = await self._repo.list_for_user(
            user_id=user.id,
            approved_only=approved_only,
            category=category,
        )
        return CareerMemoryListResponse(
            consent=consent,
            items=[CareerMemoryResponse.model_validate(r) for r in rows],
            total=total,
        )

    async def create_memory(
        self, *, user: User, payload: CareerMemoryCreateRequest
    ) -> CareerMemoryResponse:
        consent = await self.get_consent(user=user)
        if not consent.ai_consent_given:
            raise ValidationError(
                "Career Memory consent is disabled. Enable AI & Memory consent before saving."
            )

        row = await self._repo.upsert(
            user_id=user.id,
            category=payload.category,
            title=payload.title,
            content=payload.content,
            source=payload.source,
            memory_key=payload.memory_key,
            is_approved=payload.is_approved,
        )
        await self._audit.record(
            event_type="memory.saved",
            user_id=user.id,
            resource_type="career_memory",
            resource_id=str(row.id),
            details={"category": row.category, "is_approved": row.is_approved},
        )
        return CareerMemoryResponse.model_validate(row)

    async def update_memory(
        self,
        *,
        user: User,
        memory_id: uuid.UUID,
        payload: CareerMemoryUpdateRequest,
    ) -> CareerMemoryResponse:
        row = await self._repo.get_by_id(memory_id=memory_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Career memory entry not found.")

        if payload.category is not None:
            row.category = payload.category
        if payload.title is not None:
            row.title = payload.title.strip()[:200]
        if payload.content is not None:
            row.content = payload.content.strip()
        if payload.is_approved is not None:
            row.is_approved = payload.is_approved
        if payload.is_active is not None:
            row.is_active = payload.is_active

        await self._session.flush()
        await self._session.refresh(row)
        return CareerMemoryResponse.model_validate(row)

    async def delete_memory(self, *, user: User, memory_id: uuid.UUID) -> None:
        row = await self._repo.get_by_id(memory_id=memory_id, user_id=user.id)
        if row is None:
            raise NotFoundError("Career memory entry not found.")
        await self._repo.delete_entry(row)

    async def clear_memories(self, *, user: User) -> int:
        deleted = await self._repo.clear_all_for_user(user_id=user.id)
        await self._audit.record(
            event_type="memory.cleared",
            user_id=user.id,
            resource_type="career_memory",
            details={"deleted_count": deleted},
        )
        return deleted

    async def load_approved_prompt_memories(self, *, user: User) -> list[str]:
        """Return approved active memory lines for AI Co-Pilot ONLY when consent is granted."""
        consent = await self.get_consent(user=user)
        if not consent.ai_consent_given:
            return []
        rows, _ = await self._repo.list_for_user(
            user_id=user.id, approved_only=True, limit=15
        )
        return [f"[{r.category}] {r.title}: {r.content[:240]}" for r in rows]
