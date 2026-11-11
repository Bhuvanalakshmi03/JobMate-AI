"""Repositories for user career profiles and skills with strict user isolation."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile.models import UserProfile, UserSkill


class ProfileRepository:
    """Data access layer for UserProfile scoped by authenticated user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        return await self._session.scalar(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        fields: dict[str, object],
    ) -> UserProfile:
        profile = UserProfile(user_id=user_id, **fields)
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def update(
        self,
        profile: UserProfile,
        *,
        fields: dict[str, object],
    ) -> UserProfile:
        for attr, value in fields.items():
            setattr(profile, attr, value)
        await self._session.flush()
        return profile


class SkillRepository:
    """Data access layer for UserSkill scoped by authenticated user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user_id(self, user_id: uuid.UUID) -> list[UserSkill]:
        result = await self._session.scalars(
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .order_by(UserSkill.category.asc(), UserSkill.normalized_name.asc())
        )
        return list(result.all())

    async def replace_for_user(
        self,
        *,
        user_id: uuid.UUID,
        items: list[dict[str, object]],
    ) -> list[UserSkill]:
        await self._session.execute(delete(UserSkill).where(UserSkill.user_id == user_id))
        await self._session.flush()

        created: list[UserSkill] = []
        for item in items:
            skill = UserSkill(user_id=user_id, **item)
            self._session.add(skill)
            created.append(skill)

        await self._session.flush()
        return sorted(created, key=lambda s: (s.category, s.normalized_name))

