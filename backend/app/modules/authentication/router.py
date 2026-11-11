"""Authentication API v1 endpoints (/api/v1/auth/*)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.core.config import Settings
from app.core.dependencies import SettingsDep
from app.modules.authentication.dependencies import AuthServiceDep, CurrentAuthDep
from app.modules.authentication.schemas import (
    AuthConfigResponse,
    AuthSessionResponse,
    AuthUrlResponse,
    DevLoginRequest,
    LogoutResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    if settings.session_cookie_name != "careerpilot_session":
        response.delete_cookie(
            key="careerpilot_session",
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
            path="/",
        )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/config",
    response_model=AuthConfigResponse,
    summary="Get authentication provider configuration flags",
)
async def get_auth_config(service: AuthServiceDep) -> AuthConfigResponse:
    """Return non-sensitive auth capability flags."""
    return service.get_public_config()


@router.get(
    "/google",
    response_model=AuthUrlResponse,
    summary="Initiate Google OAuth 2.0 / OIDC sign-in",
)
async def initiate_google_login(
    service: AuthServiceDep,
    mode: Literal["redirect", "json"] = Query(default="redirect"),
    redirect_to: str = Query(default="/"),
) -> Response | AuthUrlResponse:
    """Generate OAuth state/PKCE challenge and redirect or return authorization URL."""
    auth_url = await service.initiate_google_login(redirect_to=redirect_to)
    if mode == "json":
        return auth_url
    return RedirectResponse(url=auth_url.authorization_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    response_model=AuthSessionResponse,
    summary="Google OAuth 2.0 / OIDC callback",
)
async def google_callback(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    mode: Literal["redirect", "json"] = Query(default="redirect"),
) -> Response | AuthSessionResponse:
    """Verify Google callback, establish HTTP-only session cookie, and redirect or return JSON."""
    session_res, redirect_path = await service.handle_google_callback(
        code=code,
        state=state,
        error=error,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    if mode == "json":
        _set_session_cookie(response, settings, session_res.access_token)
        return session_res

    target_url = f"{settings.frontend_url.rstrip('/')}{redirect_path}"
    redirect_response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
    _set_session_cookie(redirect_response, settings, session_res.access_token)
    return redirect_response


@router.post(
    "/dev-login",
    response_model=AuthSessionResponse,
    summary="Development-only sign-in (disabled in staging/production)",
)
async def dev_login(
    payload: DevLoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> AuthSessionResponse:
    """Issue a marked development session when DEV_AUTH_ENABLED=true."""
    session_res = await service.dev_login(
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    _set_session_cookie(response, settings, session_res.access_token)
    return session_res


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke current session and log out",
)
async def logout(
    request: Request,
    response: Response,
    auth_ctx: CurrentAuthDep,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> LogoutResponse:
    """Revoke server-side session record and clear session cookie."""
    await service.logout(
        session_id=auth_ctx.session_id,
        user_id=auth_ctx.user.id,
        ip_address=_client_ip(request),
    )
    _clear_session_cookie(response, settings)
    return LogoutResponse()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user",
)
async def get_current_user_info(auth_ctx: CurrentAuthDep) -> UserResponse:
    """Return authenticated user profile metadata."""
    user = auth_ctx.user
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        oauth_provider=user.oauth_provider,
        timezone=user.timezone,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        is_demo_auth=auth_ctx.is_demo_auth,
    )

