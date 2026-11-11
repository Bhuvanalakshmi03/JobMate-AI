"""Authentication business logic for Google OAuth 2.0/OIDC and session lifecycle."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import (
    create_session_token,
    decode_session_token,
    generate_pkce_pair,
    generate_random_token,
    hash_token,
)
from app.database.base import utc_now
from app.integrations.oauth.google import OAuthProviderProtocol
from app.modules.authentication.models import User
from app.modules.authentication.repository import (
    OAuthStateRepository,
    SessionRepository,
    UserRepository,
)
from app.modules.authentication.schemas import (
    AuthConfigResponse,
    AuthSessionResponse,
    AuthUrlResponse,
    DevLoginRequest,
    UserResponse,
)
from app.repositories.audit_repository import AuditLogRepository


def sanitize_redirect_path(redirect_to: str | None) -> str:
    """Ensure post-login redirect targets remain relative to the frontend origin."""
    if not redirect_to:
        return "/"
    trimmed = redirect_to.strip()
    if not trimmed.startswith("/") or trimmed.startswith("//") or "\\" in trimmed:
        return "/"
    return trimmed


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """Verified active user and session metadata attached to authenticated requests."""

    user: User
    session_id: uuid.UUID
    is_demo_auth: bool


class AuthService:
    """Coordinates OAuth sign-in, session issuance, verification, and revocation."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        oauth_provider: OAuthProviderProtocol,
    ) -> None:
        self._session = session
        self._settings = settings
        self._oauth = oauth_provider
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)
        self._oauth_states = OAuthStateRepository(session)
        self._audit = AuditLogRepository(session)

    def get_public_config(self) -> AuthConfigResponse:
        """Expose non-sensitive auth capabilities for the login screen."""
        return AuthConfigResponse(
            google_oauth_enabled=self._settings.google_oauth_configured,
            dev_auth_enabled=(
                self._settings.app_env in ("development", "testing")
                and self._settings.dev_auth_enabled
            ),
        )

    async def initiate_google_login(self, *, redirect_to: str | None = None) -> AuthUrlResponse:
        """Create single-use CSRF state + nonce + PKCE verifier and build Google auth URL."""
        raw_state = generate_random_token(32)
        nonce = generate_random_token(24)
        code_verifier, code_challenge = generate_pkce_pair()
        safe_redirect = sanitize_redirect_path(redirect_to)

        await self._oauth_states.create(
            state_hash=hash_token(raw_state),
            nonce=nonce,
            code_verifier=code_verifier,
            redirect_to=safe_redirect,
            expires_at=utc_now() + timedelta(seconds=self._settings.oauth_state_ttl_seconds),
        )
        authorization_url = self._oauth.build_authorization_url(
            state=raw_state,
            nonce=nonce,
            code_challenge=code_challenge,
        )
        return AuthUrlResponse(authorization_url=authorization_url, state=raw_state)

    async def handle_google_callback(
        self,
        *,
        code: str | None,
        state: str | None,
        error: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AuthSessionResponse, str]:
        """Validate OAuth state, verify Google OIDC identity, upsert user, and issue session."""
        if error:
            await self._audit.record(
                event_type="auth.google_denied",
                ip_address=ip_address,
                details={"provider_error": error},
            )
            raise AuthenticationError("Google sign-in was cancelled or denied.")

        if not code or not state:
            raise AuthenticationError("Missing OAuth authorization code or state.")

        oauth_state = await self._oauth_states.consume_valid(state_hash=hash_token(state))
        if oauth_state is None:
            await self._audit.record(
                event_type="auth.invalid_oauth_state",
                ip_address=ip_address,
            )
            raise AuthenticationError("OAuth state is invalid, expired, or already used.")

        identity = await self._oauth.exchange_and_verify(
            code=code,
            code_verifier=oauth_state.code_verifier,
            expected_nonce=oauth_state.nonce,
        )

        user = await self._users.get_by_oauth_identity(
            provider=identity.provider,
            subject=identity.subject,
        )
        if user is None:
            user = await self._users.get_by_email(identity.email)
            if user is not None:
                user.oauth_provider = identity.provider
                user.oauth_subject = identity.subject
                await self._users.update_login_metadata(
                    user,
                    full_name=identity.full_name,
                    avatar_url=identity.avatar_url,
                )
            else:
                user = await self._users.create(
                    email=identity.email,
                    full_name=identity.full_name,
                    oauth_provider=identity.provider,
                    oauth_subject=identity.subject,
                    avatar_url=identity.avatar_url,
                )
        else:
            await self._users.update_login_metadata(
                user,
                full_name=identity.full_name,
                avatar_url=identity.avatar_url,
            )

        if not user.is_active:
            raise AuthorizationError("This user account has been deactivated.")

        session_response = await self._issue_user_session(
            user=user,
            is_demo_auth=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._audit.record(
            event_type="auth.google_login",
            user_id=user.id,
            resource_type="user_session",
            ip_address=ip_address,
        )
        return session_response, oauth_state.redirect_to

    async def dev_login(
        self,
        *,
        payload: DevLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSessionResponse:
        """Issue a clearly marked development session when DEV_AUTH_ENABLED=true."""
        if (
            self._settings.app_env not in ("development", "testing")
            or not self._settings.dev_auth_enabled
        ):
            raise AuthorizationError("Development sign-in is disabled.")

        user = await self._users.get_by_email(payload.email)
        if user is None:
            user = await self._users.create(
                email=payload.email,
                full_name=payload.full_name,
                oauth_provider="dev",
                oauth_subject=f"dev:{payload.email}",
                timezone=payload.timezone,
            )
        else:
            await self._users.update_login_metadata(user, full_name=payload.full_name)

        if not user.is_active:
            raise AuthorizationError("This user account has been deactivated.")

        session_response = await self._issue_user_session(
            user=user,
            is_demo_auth=True,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._audit.record(
            event_type="auth.dev_login",
            user_id=user.id,
            resource_type="user_session",
            ip_address=ip_address,
            details={"is_demo_auth": True},
        )
        return session_response

    async def authenticate_token(self, raw_token: str) -> AuthenticatedSession:
        """Verify JWT token signature/expiry and confirm active non-revoked DB session."""
        user_id, session_id = decode_session_token(
            token=raw_token,
            secret_key=self._settings.app_secret_key,
        )
        active_session = await self._sessions.get_active(
            session_id=session_id,
            token_hash=hash_token(raw_token),
        )
        if active_session is None or active_session.user_id != user_id:
            raise AuthenticationError("Session has expired or been revoked.")

        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Authenticated user account is unavailable.")

        return AuthenticatedSession(
            user=user,
            session_id=active_session.id,
            is_demo_auth=active_session.is_demo_auth,
        )

    async def logout(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Revoke the active session and record logout audit event."""
        await self._sessions.revoke(session_id=session_id, user_id=user_id)
        await self._audit.record(
            event_type="auth.logout",
            user_id=user_id,
            resource_type="user_session",
            resource_id=str(session_id),
            ip_address=ip_address,
        )

    async def _issue_user_session(
        self,
        *,
        user: User,
        is_demo_auth: bool,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthSessionResponse:
        session_id = uuid.uuid4()
        token, expires_at = create_session_token(
            user_id=user.id,
            session_id=session_id,
            secret_key=self._settings.app_secret_key,
            ttl_seconds=self._settings.session_ttl_seconds,
        )
        await self._sessions.create(
            session_id=session_id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            is_demo_auth=is_demo_auth,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        user_dto = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            oauth_provider=user.oauth_provider,
            timezone=user.timezone,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            is_demo_auth=is_demo_auth,
        )
        return AuthSessionResponse(
            user=user_dto,
            access_token=token,
            expires_at=expires_at,
            is_demo_auth=is_demo_auth,
        )

