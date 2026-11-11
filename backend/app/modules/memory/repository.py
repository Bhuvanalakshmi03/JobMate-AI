"""Repository for user-isolated consent-gated Career Memory records."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models import CareerMemory


class CareerMemoryRepository:
    """Data access layer strictly scoped by user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, *, memory_id: uuid.UUID, user_id: uuid.UUID
    ) -> CareerMemory | None:
        return await self._session.scalar(
            select(CareerMemory).where(
                CareerMemory.id == memory_id,
                CareerMemory.user_id == user_id,
            )
        )

    async def get_by_key(self, *, user_id: uuid.UUID, memory_key: str) -> CareerMemory | None:
        return await self._session.scalar(
            select(CareerMemory).where(
                CareerMemory.user_id == user_id,
                CareerMemory.memory_key == memory_key,
            )
        )

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        approved_only: bool = False,
        category: str | None = None,
        limit: int = 50,
    ) -> tuple[list[CareerMemory], int]:
        stmt = select(CareerMemory).where(CareerMemory.user_id == user_id)
        count_stmt = (
            select(func.count())
            .select_from(CareerMemory)
            .where(CareerMemory.user_id == user_id)
        )
        if approved_only:
            stmt = stmt.where(CareerMemory.is_approved.is_(True), CareerMemory.is_active.is_(True))
            count_stmt = count_stmt.where(
                CareerMemory.is_approved.is_(True), CareerMemory.is_active.is_(True)
            )
        if category:
            stmt = stmt.where(CareerMemory.category == category)
            count_stmt = count_stmt.where(CareerMemory.category == category)

        total = int((await self._session.scalar(count_stmt)) or 0)
        rows = list(
            (
                await self._session.scalars(
                    stmt.order_by(CareerMemory.updated_at.desc()).limit(limit)
                )
            ).all()
        )
        return rows, total

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        category: str,
        title: str,
        content: str,
        source: str,
        memory_key: str | None,
        is_approved: bool,
    ) -> CareerMemory:
        clean_key = memory_key.strip()[:120] if memory_key and memory_key.strip() else None
        if clean_key is not None:
            existing = await self.get_by_key(user_id=user_id, memory_key=clean_key)
            if existing is not None:
                existing.category = category
                existing.title = title.strip()[:200]
                existing.content = content.strip()
                existing.source = source
                existing.is_approved = is_approved
                existing.is_active = True
                await self._session.flush()
                await self._session.refresh(existing)
                return existing

        row = CareerMemory(
            user_id=user_id,
            category=category,
            title=title.strip()[:200],
            content=content.strip(),
            source=source,
            memory_key=clean_key,
            is_approved=is_approved,
            is_active=True,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete_entry(self, row: CareerMemory) -> None:
        await self._session.delete(row)
        await self._session.flush()

    async def clear_all_for_user(self, *, user_id: uuid.UUID) -> int:
        res = await self._session.execute(
            delete(CareerMemory).where(CareerMemory.user_id == user_id)
        )
        await self._session.flush()
        return int(getattr(res, "rowcount", 0) or 0)
