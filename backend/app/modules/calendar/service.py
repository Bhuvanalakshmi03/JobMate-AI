"""Google Calendar business logic: OAuth connection, token refresh, and event ops."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_pkce_pair,
    generate_random_token,
    hash_token,
    sanitize_redirect_path,
)
from app.database.base import utc_now
from app.integrations.calendar.google_calendar import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    CalendarEventRecord,
    CalendarProviderProtocol,
    GoogleCalendarClient,
)
from app.integrations.oauth.google import GoogleOAuthClient, OAuthIdentity
from app.modules.authentication.models import User
from app.modules.authentication.repository import OAuthStateRepository
from app.modules.authentication.schemas import AuthUrlResponse
from app.modules.calendar.repository import CalendarConnectionRepository
from app.modules.calendar.schemas import (
    CalendarEventCreateRequest,
    CalendarEventItem,
    CalendarEventsResponse,
    CalendarStatusResponse,
)
from app.repositories.audit_repository import AuditLogRepository


class CalendarService:
    """Coordinates encrypted Google Calendar token storage, refresh, and event CRUD."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        provider: CalendarProviderProtocol | None = None,
        oauth_client: GoogleOAuthClient | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._provider: CalendarProviderProtocol = provider or GoogleCalendarClient(
            timeout_seconds=float(settings.request_timeout_seconds)
        )
        self._oauth = oauth_client or GoogleOAuthClient(settings)
        self._repo = CalendarConnectionRepository(session)
        self._oauth_states = OAuthStateRepository(session)
        self._audit = AuditLogRepository(session)

    async def initiate_connect(
        self,
        *,
        user: User,
        redirect_to: str = "/copilot",
    ) -> AuthUrlResponse:
        """Build an incremental Google OAuth URL requesting calendar.events consent."""
        raw_state = generate_random_token(32)
        nonce = generate_random_token(24)
        code_verifier, code_challenge = generate_pkce_pair()
        safe_redirect = sanitize_redirect_path(redirect_to)

        await self._oauth_states.create(
            state_hash=hash_token(raw_state),
            nonce=nonce,
            code_verifier=code_verifier,
            redirect_to=safe_redirect,
            flow_type="calendar_connect",
            user_id=user.id,
            expires_at=utc_now() + timedelta(seconds=self._settings.oauth_state_ttl_seconds),
        )
        authorization_url = self._oauth.build_authorization_url(
            state=raw_state,
            nonce=nonce,
            code_challenge=code_challenge,
            extra_scopes=(GOOGLE_CALENDAR_EVENTS_SCOPE,),
            prompt_override="consent",
        )
        return AuthUrlResponse(authorization_url=authorization_url, state=raw_state)

    async def save_oauth_connection(
        self,
        *,
        user_id: uuid.UUID,
        identity: OAuthIdentity,
    ) -> None:
        """Encrypt and persist Google Calendar OAuth tokens obtained via OAuth callback."""
        if not identity.access_token:
            raise ValidationError("Google OAuth callback did not provide a Calendar access token.")

        expires_at = (
            utc_now() + timedelta(seconds=max(60, int(identity.expires_in)))
            if identity.expires_in
            else utc_now() + timedelta(hours=1)
        )
        enc_access = encrypt_secret(
            identity.access_token, secret_key=self._settings.app_secret_key
        )
        enc_refresh = (
            encrypt_secret(identity.refresh_token, secret_key=self._settings.app_secret_key)
            if identity.refresh_token
            else None
        )
        await self._repo.upsert_for_user(
            user_id=user_id,
            google_email=identity.email,
            encrypted_access_token=enc_access,
            encrypted_refresh_token=enc_refresh,
            token_expires_at=expires_at,
            scopes=identity.scope or GOOGLE_CALENDAR_EVENTS_SCOPE,
        )
        await self._audit.record(
            event_type="calendar.connected",
            user_id=user_id,
            resource_type="google_calendar",
            details={"google_email": identity.email},
        )

    async def get_status(self, *, user_id: uuid.UUID) -> CalendarStatusResponse:
        conn = await self._repo.get_by_user_id(user_id)
        if conn is None:
            return CalendarStatusResponse(connected=False)
        scope_list = [s.strip() for s in conn.scopes.split() if s.strip()]
        return CalendarStatusResponse(
            connected=True,
            google_email=conn.google_email,
            scopes=scope_list,
            token_expires_at=conn.token_expires_at,
        )

    async def _require_valid_access_token(self, *, user_id: uuid.UUID) -> str:
        conn = await self._repo.get_by_user_id(user_id)
        if conn is None:
            raise ValidationError(
                "Google Calendar is not connected. Click 'Connect Google Calendar' first."
            )

        access_token = decrypt_secret(
            conn.encrypted_access_token, secret_key=self._settings.app_secret_key
        )
        needs_refresh = (
            conn.token_expires_at is not None
            and conn.token_expires_at <= utc_now() + timedelta(seconds=120)
        )
        if needs_refresh and conn.encrypted_refresh_token:
            refresh_token = decrypt_secret(
                conn.encrypted_refresh_token, secret_key=self._settings.app_secret_key
            )
            new_access, expires_in = await self._oauth.refresh_access_token(
                refresh_token=refresh_token
            )
            conn.encrypted_access_token = encrypt_secret(
                new_access, secret_key=self._settings.app_secret_key
            )
            conn.token_expires_at = utc_now() + timedelta(seconds=max(60, expires_in))
            await self._session.flush()
            return new_access

        return access_token

    async def list_upcoming_events(
        self,
        *,
        user_id: uuid.UUID,
        days_ahead: int = 14,
        max_results: int = 15,
    ) -> CalendarEventsResponse:
        conn = await self._repo.get_by_user_id(user_id)
        if conn is None:
            return CalendarEventsResponse(connected=False, items=[])

        token = await self._require_valid_access_token(user_id=user_id)
        now = datetime.now(UTC)
        max_dt = now + timedelta(days=max(1, min(days_ahead, 90)))
        records: list[CalendarEventRecord] = await self._provider.list_events(
            access_token=token,
            time_min_iso=now.isoformat(),
            time_max_iso=max_dt.isoformat(),
            max_results=max_results,
        )
        return CalendarEventsResponse(
            connected=True,
            items=[
                CalendarEventItem(
                    event_id=r.event_id,
                    summary=r.summary,
                    start_iso=r.start_iso,
                    end_iso=r.end_iso,
                    location=r.location,
                    description=r.description,
                    html_link=r.html_link,
                    status=r.status,
                )
                for r in records
            ],
        )

    async def create_event(
        self,
        *,
        user: User,
        payload: CalendarEventCreateRequest,
    ) -> CalendarEventItem:
        token = await self._require_valid_access_token(user_id=user.id)
        tz = (payload.timezone or user.timezone or "UTC").strip()
        created = await self._provider.create_event(
            access_token=token,
            summary=payload.summary,
            start_iso=payload.start_iso,
            end_iso=payload.end_iso,
            description=payload.description,
            location=payload.location,
            timezone=tz,
        )
        await self._audit.record(
            event_type="calendar.event_created",
            user_id=user.id,
            resource_type="calendar_event",
            resource_id=created.event_id,
            details={"summary": created.summary, "start_iso": created.start_iso},
        )
        return CalendarEventItem(
            event_id=created.event_id,
            summary=created.summary,
            start_iso=created.start_iso,
            end_iso=created.end_iso,
            location=created.location,
            description=created.description,
            html_link=created.html_link,
            status=created.status,
        )

    async def disconnect(self, *, user_id: uuid.UUID) -> None:
        await self._repo.delete_for_user(user_id)
        await self._audit.record(
            event_type="calendar.disconnected",
            user_id=user_id,
            resource_type="google_calendar",
        )
