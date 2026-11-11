"""Google OAuth 2.0 / OIDC adapter with PKCE, state, nonce, issuer, and audience validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConfigurationError, ExternalServiceError
from app.core.security import constant_time_compare

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  # nosec B105
GOOGLE_VALID_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


@dataclass(frozen=True, slots=True)
class OAuthIdentity:
    """Verified OIDC user identity and optional OAuth tokens returned by provider."""

    provider: str
    subject: str
    email: str
    email_verified: bool
    full_name: str
    avatar_url: str | None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None


class OAuthProviderProtocol(Protocol):
    """Protocol enabling dependency-injected OAuth provider replacement in tests."""

    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str: ...

    async def exchange_and_verify(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> OAuthIdentity: ...


class GoogleOAuthClient:
    """Production Google OAuth 2.0 / OIDC adapter."""

    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.google_client_id.strip()
        self._client_secret = settings.google_client_secret.strip()
        self._redirect_uri = settings.google_redirect_uri.strip()
        self._timeout = settings.request_timeout_seconds

    def _ensure_configured(self) -> None:
        if not self._client_id or not self._client_secret:
            raise ConfigurationError(
                "Google OAuth credentials are not configured on the backend."
            )

    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
        extra_scopes: tuple[str, ...] = (),
        prompt_override: str | None = None,
    ) -> str:
        """Construct Google OIDC authorization URL with PKCE S256 and nonce."""
        self._ensure_configured()
        scopes = ["openid", "email", "profile", *extra_scopes]
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": prompt_override or "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def refresh_access_token(self, *, refresh_token: str) -> tuple[str, int]:
        """Exchange a stored offline refresh token for a fresh Google access token."""
        self._ensure_configured()
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(GOOGLE_TOKEN_URL, data=payload)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to contact Google OAuth refresh endpoint.") from exc

        if response.status_code != 200:
            raise AuthenticationError(
                "Google Calendar authorization expired or was revoked. Please reconnect."
            )

        data: dict[str, Any] = response.json()
        new_access = str(data.get("access_token") or "").strip()
        if not new_access:
            raise AuthenticationError("Google refresh response did not return an access token.")
        expires_in = int(data.get("expires_in") or 3600)
        return new_access, expires_in

    async def exchange_and_verify(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> OAuthIdentity:
        """Exchange authorization code for tokens and verify the Google OIDC ID token."""
        self._ensure_configured()

        payload = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(GOOGLE_TOKEN_URL, data=payload)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to contact Google OAuth token endpoint.") from exc

        if response.status_code != 200:
            raise AuthenticationError("Google authorization code exchange failed.")

        token_data: dict[str, Any] = response.json()
        raw_id_token = token_data.get("id_token")
        if not isinstance(raw_id_token, str) or not raw_id_token:
            raise AuthenticationError("Google response did not include an OIDC ID token.")

        try:
            claims: dict[str, Any] = google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                raw_id_token,
                google_requests.Request(),
                audience=self._client_id,
            )
        except Exception as exc:
            raise AuthenticationError("Google ID token validation failed.") from exc

        issuer = str(claims.get("iss", ""))
        if issuer not in GOOGLE_VALID_ISSUERS:
            raise AuthenticationError("Unexpected Google OIDC token issuer.")

        token_nonce = str(claims.get("nonce", ""))
        if not token_nonce or not constant_time_compare(token_nonce, expected_nonce):
            raise AuthenticationError("OIDC nonce validation failed.")

        if not bool(claims.get("email_verified", False)):
            raise AuthenticationError("Google account email address is not verified.")

        subject = str(claims.get("sub", "")).strip()
        email = str(claims.get("email", "")).strip().lower()
        if not subject or not email:
            raise AuthenticationError("Google ID token is missing required user claims.")

        full_name = str(claims.get("name") or email.split("@", 1)[0]).strip()
        avatar = claims.get("picture")
        avatar_url = str(avatar).strip() if isinstance(avatar, str) and avatar.strip() else None

        return OAuthIdentity(
            provider="google",
            subject=subject,
            email=email,
            email_verified=True,
            full_name=full_name,
            avatar_url=avatar_url,
            access_token=(
                str(token_data["access_token"]).strip()
                if isinstance(token_data.get("access_token"), str)
                else None
            ),
            refresh_token=(
                str(token_data["refresh_token"]).strip()
                if isinstance(token_data.get("refresh_token"), str)
                else None
            ),
            expires_in=(
                int(token_data["expires_in"])
                if isinstance(token_data.get("expires_in"), int | float)
                else None
            ),
            scope=(
                str(token_data["scope"]).strip()
                if isinstance(token_data.get("scope"), str)
                else None
            ),
        )
