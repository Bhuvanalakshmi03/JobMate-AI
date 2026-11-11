"""Cryptographic, PKCE, and JWT session token helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.exceptions import AuthenticationError

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "careerpilot-api"
JWT_AUDIENCE = "careerpilot-client"


def generate_random_token(nbytes: int = 32) -> str:
    """Generate a URL-safe cryptographically random token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """Return hex SHA-256 digest of a token or state value for safe DB storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def constant_time_compare(left: str, right: str) -> bool:
    """Compare two strings in constant time."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE (code_verifier, S256 code_challenge) pair."""
    code_verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def create_session_token(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    secret_key: str,
    ttl_seconds: int,
) -> tuple[str, datetime]:
    """Sign an HS256 session JWT containing subject and session ID."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_session_token(*, token: str, secret_key: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Verify session JWT signature, issuer, audience, and expiry; return (user_id, session_id)."""
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "sid", "exp", "iat", "iss", "aud"]},
        )
        user_id = uuid.UUID(str(claims["sub"]))
        session_id = uuid.UUID(str(claims["sid"]))
        return user_id, session_id
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AuthenticationError("Session token is invalid or has expired.") from exc

