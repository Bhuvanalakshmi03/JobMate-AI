"""Unit and API tests for Google OAuth, JWT session lifecycle, revocation, and dev auth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
from fastapi import FastAPI

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import JWT_AUDIENCE, JWT_ISSUER
from app.integrations.oauth.google import OAuthIdentity
from app.modules.authentication.dependencies import get_oauth_provider


class FakeGoogleOAuthProvider:
    """Deterministic fake OAuth/OIDC provider for authentication tests."""

    def __init__(self, identity: OAuthIdentity | None = None, fail_exchange: bool = False) -> None:
        self.identity = identity or OAuthIdentity(
            provider="google",
            subject="google-sub-12345",
            email="alex.student@university.edu",
            email_verified=True,
            full_name="Alex Student",
            avatar_url="https://example.com/avatar.png",
        )
        self.fail_exchange = fail_exchange
        self.last_expected_nonce: str | None = None

    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str:
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?state={state}&nonce={nonce}&code_challenge={code_challenge}"
        )

    async def exchange_and_verify(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> OAuthIdentity:
        self.last_expected_nonce = expected_nonce
        if self.fail_exchange or code != "valid-auth-code" or not code_verifier:
            raise AuthenticationError("Google authorization code exchange failed.")
        return self.identity


async def test_google_oauth_flow_login_me_and_logout_revocation(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    fake_oauth = FakeGoogleOAuthProvider()
    migrated_test_app.dependency_overrides[get_oauth_provider] = lambda: fake_oauth

    async with migrated_test_app.router.lifespan_context(migrated_test_app):
        transport = httpx.ASGITransport(app=migrated_test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            init_res = await client.get("/api/v1/auth/google?mode=json&redirect_to=/profile")
            assert init_res.status_code == 200
            init_data = init_res.json()
            state = init_data["state"]
            parsed_qs = parse_qs(urlparse(init_data["authorization_url"]).query)
            assert parsed_qs["state"] == [state]

            cb_res = await client.get(
                f"/api/v1/auth/google/callback?code=valid-auth-code&state={state}&mode=json"
            )
            assert cb_res.status_code == 200
            session_payload = cb_res.json()
            assert session_payload["user"]["email"] == "alex.student@university.edu"
            assert session_payload["is_demo_auth"] is False
            token = session_payload["access_token"]
            assert test_settings.session_cookie_name in cb_res.cookies

            # Replay of the exact same OAuth state must fail
            replay_res = await client.get(
                f"/api/v1/auth/google/callback?code=valid-auth-code&state={state}&mode=json"
            )
            assert replay_res.status_code == 401

            # Authenticated /auth/me succeeds via cookie or bearer
            me_res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_res.status_code == 200
            assert me_res.json()["full_name"] == "Alex Student"

            # Logout revokes the session
            logout_res = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert logout_res.status_code == 200
            assert logout_res.json()["logged_out"] is True

            # Reusing revoked token must be rejected
            after_logout_res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert after_logout_res.status_code == 401


async def test_invalid_oauth_callback_and_denied_error(migrated_test_app: FastAPI) -> None:
    fake_oauth = FakeGoogleOAuthProvider()
    migrated_test_app.dependency_overrides[get_oauth_provider] = lambda: fake_oauth

    async with migrated_test_app.router.lifespan_context(migrated_test_app):
        transport = httpx.ASGITransport(app=migrated_test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            bad_state = await client.get(
                "/api/v1/auth/google/callback?code=valid-auth-code&state=forged-state&mode=json"
            )
            assert bad_state.status_code == 401

            denied = await client.get(
                "/api/v1/auth/google/callback?error=access_denied&mode=json"
            )
            assert denied.status_code == 401


async def test_expired_and_unauthenticated_tokens_rejected(
    async_client: httpx.AsyncClient,
    test_settings: Settings,
) -> None:
    unauth = await async_client.get("/api/v1/auth/me")
    assert unauth.status_code == 401

    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        test_settings.app_secret_key,
        algorithm="HS256",
    )
    expired_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_res.status_code == 401


async def test_dev_login_disabled_by_default_and_works_when_enabled(
    migrated_test_app: FastAPI,
    test_settings: Settings,
) -> None:
    async with migrated_test_app.router.lifespan_context(migrated_test_app):
        transport = httpx.ASGITransport(app=migrated_test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            cfg = await client.get("/api/v1/auth/config")
            assert cfg.status_code == 200
            assert cfg.json()["dev_auth_enabled"] is False

            blocked = await client.post("/api/v1/auth/dev-login", json={})
            assert blocked.status_code == 403

    # Now enable dev_auth_enabled explicitly in testing settings
    dev_settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    from app.main import create_app

    dev_app = create_app(settings=dev_settings)
    async with dev_app.router.lifespan_context(dev_app):
        transport = httpx.ASGITransport(app=dev_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.post(
                "/api/v1/auth/dev-login",
                json={"email": "dev.student@example.edu", "full_name": "Dev Student"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["is_demo_auth"] is True
            assert data["user"]["email"] == "dev.student@example.edu"


async def test_google_oauth_client_validates_nonce_issuer_and_verified_email(
    monkeypatch: object,
) -> None:
    import pytest

    from app.integrations.oauth.google import GoogleOAuthClient

    assert isinstance(monkeypatch, pytest.MonkeyPatch)
    oauth_settings = Settings(
        google_client_id="client-123.apps.googleusercontent.com",
        google_client_secret="client-secret-xyz",
        google_redirect_uri="http://localhost:8000/api/v1/auth/google/callback",
    )
    client = GoogleOAuthClient(oauth_settings)
    auth_url = client.build_authorization_url(
        state="state-1",
        nonce="nonce-1",
        code_challenge="challenge-1",
    )
    assert "code_challenge_method=S256" in auth_url
    assert "nonce=nonce-1" in auth_url

    class FakeHttpResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"id_token": "fake-jwt"}

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, data: dict[str, str]) -> FakeHttpResponse:
            return FakeHttpResponse()

    monkeypatch.setattr("app.integrations.oauth.google.httpx.AsyncClient", FakeAsyncClient)

    # Bad nonce rejected
    monkeypatch.setattr(
        "app.integrations.oauth.google.google_id_token.verify_oauth2_token",
        lambda *_args, **_kwargs: {
            "iss": "https://accounts.google.com",
            "sub": "sub-1",
            "email": "u@edu.org",
            "email_verified": True,
            "nonce": "wrong-nonce",
        },
    )
    with pytest.raises(AuthenticationError, match="nonce"):
        await client.exchange_and_verify(
            code="code-1",
            code_verifier="verifier-1",
            expected_nonce="nonce-1",
        )

    # Unverified email rejected
    monkeypatch.setattr(
        "app.integrations.oauth.google.google_id_token.verify_oauth2_token",
        lambda *_args, **_kwargs: {
            "iss": "https://accounts.google.com",
            "sub": "sub-1",
            "email": "u@edu.org",
            "email_verified": False,
            "nonce": "nonce-1",
        },
    )
    with pytest.raises(AuthenticationError, match="not verified"):
        await client.exchange_and_verify(
            code="code-1",
            code_verifier="verifier-1",
            expected_nonce="nonce-1",
        )

    # Valid claims succeed
    monkeypatch.setattr(
        "app.integrations.oauth.google.google_id_token.verify_oauth2_token",
        lambda *_args, **_kwargs: {
            "iss": "https://accounts.google.com",
            "sub": "sub-1",
            "email": "U@Edu.Org",
            "email_verified": True,
            "nonce": "nonce-1",
            "name": "Student Name",
        },
    )
    identity = await client.exchange_and_verify(
        code="code-1",
        code_verifier="verifier-1",
        expected_nonce="nonce-1",
    )
    assert identity.email == "u@edu.org"
    assert identity.subject == "sub-1"
