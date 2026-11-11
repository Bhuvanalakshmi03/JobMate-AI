"""Repository for persisting immutable security and workflow audit logs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_ctx, sanitize_log_value
from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Writes sanitized audit log records within the caller's database transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        event_type: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create and flush an immutable audit log entry."""
        safe_details = sanitize_log_value(details) if details is not None else None
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id_ctx.get(),
            ip_address=ip_address,
            details=safe_details,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

