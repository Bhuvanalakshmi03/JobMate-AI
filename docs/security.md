# CareerPilot AI — Security Controls

## Authentication & Sessions
- **OAuth 2.0 / OIDC:** Uses single-use hashed CSRF `state`, OIDC `nonce` verification, PKCE (`S256`), and Google ID token verification checking `iss`, `aud`, `exp`, and `email_verified`.
- **Open Redirect Prevention:** Post-login `redirect_to` parameters are sanitized to allow only relative single-slash paths (`/`).
- **Revocable Sessions:** Signed HS256 JWTs carry a `sid` (session UUID) backed by SHA-256 `token_hash` records in `user_sessions`. Logout immediately sets `revoked_at` so compromised or logged-out tokens cannot be replayed.
- **Development Auth Guard:** `DEV_AUTH_ENABLED=true` is rejected by `Settings` validation in `staging` and `production` environments.

## Authorization & Data Isolation
- Every query in `ProfileRepository` and `SkillRepository` scopes strictly to `current_user.id` derived from the verified server-side session.
- Profile and skill endpoints do not accept arbitrary `user_id` parameters.

## Input Validation & Logging
- IANA timezones are validated via Python `zoneinfo.ZoneInfo`.
- External links (`linkedin_url`, `github_url`, `portfolio_url`) restrict schemes to `http://` and `https://`.
- Structured JSON logs recursively redact sensitive keys (`token`, `secret`, `api_key`, `password`, `resume_text`, `raw_text`).
- Centralized exception handling omits internal stack traces from API responses.

