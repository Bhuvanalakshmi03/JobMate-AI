"""Database repositories for users, sessions, and OAuth states."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utc_now
from app.modules.authentication.models import OAuthState, User, UserSession


class UserRepository:
    """Data access layer for User accounts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.scalar(select(User).where(User.id == user_id))

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email.strip().lower()))

    async def get_by_oauth_identity(self, *, provider: str, subject: str) -> User | None:
        return await self._session.scalar(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_subject == subject,
            )
        )

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        oauth_provider: str,
        oauth_subject: str,
        avatar_url: str | None = None,
        timezone: str = "UTC",
    ) -> User:
        user = User(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_subject=oauth_subject,
            timezone=timezone,
            last_login_at=utc_now(),
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_login_metadata(
        self,
        user: User,
        *,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        if full_name:
            user.full_name = full_name.strip()
        if avatar_url is not None:
            user.avatar_url = avatar_url
        user.last_login_at = utc_now()
        await self._session.flush()
        return user


class SessionRepository:
    """Data access layer for revocable UserSession records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        is_demo_auth: bool = False,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> UserSession:
        record = UserSession(
            id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_demo_auth=is_demo_auth,
            user_agent=user_agent[:512] if user_agent else None,
            ip_address=ip_address[:64] if ip_address else None,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_active(self, *, session_id: uuid.UUID, token_hash: str) -> UserSession | None:
        now = utc_now()
        return await self._session.scalar(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
        )

    async def revoke(self, *, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now())
        )
        await self._session.flush()


class OAuthStateRepository:
    """Data access layer for single-use OAuth CSRF state and nonce tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        state_hash: str,
        nonce: str,
        code_verifier: str,
        redirect_to: str,
        expires_at: datetime,
    ) -> OAuthState:
        record = OAuthState(
            state_hash=state_hash,
            nonce=nonce,
            code_verifier=code_verifier,
            redirect_to=redirect_to,
            expires_at=expires_at,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def consume_valid(self, *, state_hash: str) -> OAuthState | None:
        now = utc_now()
        record = await self._session.scalar(
            select(OAuthState).where(
                OAuthState.state_hash == state_hash,
                OAuthState.consumed_at.is_(None),
                OAuthState.expires_at > now,
            )
        )
        if record is None:
            return None
        record.consumed_at = now
        await self._session.flush()
        return record

