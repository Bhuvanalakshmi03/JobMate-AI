"""FastAPI authentication dependencies extracting and validating the current user."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request

from app.core.dependencies import DBSessionDep, SettingsDep
from app.core.exceptions import AuthenticationError
from app.core.logging import user_id_ctx
from app.integrations.oauth.google import GoogleOAuthClient, OAuthProviderProtocol
from app.modules.authentication.models import User
from app.modules.authentication.service import AuthenticatedSession, AuthService


def get_oauth_provider(settings: SettingsDep) -> OAuthProviderProtocol:
    """Provide the configured OAuth/OIDC provider adapter."""
    return GoogleOAuthClient(settings)


OAuthProviderDep = Annotated[OAuthProviderProtocol, Depends(get_oauth_provider)]


def get_auth_service(
    session: DBSessionDep,
    settings: SettingsDep,
    oauth_provider: OAuthProviderDep,
) -> AuthService:
    """Build request-scoped AuthService."""
    return AuthService(session=session, settings=settings, oauth_provider=oauth_provider)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def extract_session_token(request: Request, cookie_name: str) -> str:
    """Extract session JWT from Authorization Bearer header or HTTP-only cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            return parts[1].strip()
        raise AuthenticationError("Malformed Authorization header.")

    cookie_token = request.cookies.get(cookie_name) or request.cookies.get(
        "careerpilot_session"
    )
    if cookie_token and cookie_token.strip():
        return cookie_token.strip()

    raise AuthenticationError("Authentication credentials were not provided.")


async def get_current_auth(
    request: Request,
    settings: SettingsDep,
    auth_service: AuthServiceDep,
) -> AsyncGenerator[AuthenticatedSession, None]:
    """Authenticate request token and bind user_id into structured logging context."""
    raw_token = extract_session_token(request, settings.session_cookie_name)
    auth_ctx = await auth_service.authenticate_token(raw_token)
    log_token = user_id_ctx.set(str(auth_ctx.user.id))
    try:
        yield auth_ctx
    finally:
        user_id_ctx.reset(log_token)


CurrentAuthDep = Annotated[AuthenticatedSession, Depends(get_current_auth)]


async def get_current_user(auth_ctx: CurrentAuthDep) -> User:
    """Return authenticated User ORM model."""
    return auth_ctx.user


CurrentUserDep = Annotated[User, Depends(get_current_user)]

