"""Unit tests for structured JSON logging and sensitive field redaction."""

from __future__ import annotations

import json
import logging

from app.core.logging import StructuredJsonFormatter, request_id_ctx, sanitize_log_value


def test_sanitize_log_value_redacts_secrets_and_resume_payloads() -> None:
    raw = {
        "user_id": "123",
        "openai_api_key": "sk-live-secret",
        "nested": {
            "resume_text": "Full private resume text",
            "safe_note": "ok",
        },
        "tokens": ["secret-a"],
        "items": [{"access_token": "jwt-value", "label": "session"}],
    }
    sanitized = sanitize_log_value(raw)
    assert sanitized["user_id"] == "123"
    assert sanitized["openai_api_key"] == "[REDACTED]"
    assert sanitized["nested"]["resume_text"] == "[REDACTED]"
    assert sanitized["nested"]["safe_note"] == "ok"
    assert sanitized["tokens"] == "[REDACTED]"
    assert sanitized["items"][0]["access_token"] == "[REDACTED]"
    assert sanitized["items"][0]["label"] == "session"


def test_structured_json_formatter_includes_request_context() -> None:
    formatter = StructuredJsonFormatter()
    token = request_id_ctx.set("req-abc-123")
    try:
        record = logging.LogRecord(
            name="jobmate.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Test log message",
            args=(),
            exc_info=None,
        )
        record.api_key = "secret-val"
        record.stage = "init"
        parsed = json.loads(formatter.format(record))
    finally:
        request_id_ctx.reset(token)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test log message"
    assert parsed["request_id"] == "req-abc-123"
    assert parsed["api_key"] == "[REDACTED]"
    assert parsed["stage"] == "init"

