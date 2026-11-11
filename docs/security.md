# CareerPilot AI — Security Controls

## Authentication & Sessions
- **OAuth 2.0 / OIDC:** Uses single-use hashed CSRF `state`, OIDC `nonce` verification, PKCE (`S256`), and Google ID token verification checking `iss`, `aud`, `exp`, and `email_verified`.
- **Open Redirect Prevention:** Post-login `redirect_to` parameters are sanitized to allow only relative single-slash paths (`/`).
- **Revocable Sessions:** Signed HS256 JWTs carry a `sid` (session UUID) backed by SHA-256 `token_hash` records in `user_sessions`.
- **Development Auth Guard:** `DEV_AUTH_ENABLED=true` is rejected by `Settings` validation in `staging` and `production`.

## Authorization & Data Isolation
- Every query in `ProfileRepository`, `SkillRepository`, `ResumeRepository`, and `ResumeFactRepository` scopes strictly to `current_user.id` derived from the verified server-side session.

## Resume Upload, Storage & AI Security
- **File Validation:** Enforces `.pdf`/`.docx` extensions, size limits (`MAX_RESUME_SIZE_BYTES`), page limits (`MAX_RESUME_PAGES`), MIME checks, `%PDF-` / DOCX ZIP magic signatures, and DOCX uncompressed-size zip-bomb bounds.
- **Private Storage:** Original files are saved under UUID-based keys via `LocalPrivateStorage` with strict path-traversal rejection and `O_EXCL` non-overwriting creation; files are never executed or served statically.
- **AI Prompt Injection & Fact Grounding:** Resume text is isolated inside `<untrusted_resume_text>` delimiters with explicit instruction-ignoring rules. `ResumeExtractionValidator` verifies LLM JSON schemas and checks whether `evidence_excerpt` appears in the extracted resume text, lowering confidence and flagging ungrounded claims.
- **Verification Gate:** Unverified or rejected facts are never synced to `user_profiles` or `user_skills`.

## Input Validation & Logging
- IANA timezones are validated via Python `zoneinfo.ZoneInfo`; external links restrict schemes to `http://` and `https://`.
- Structured JSON logs recursively redact sensitive keys (`token`, `secret`, `api_key`, `password`, `resume_text`, `raw_text`).
- Centralized exception handling omits internal stack traces from API responses.
