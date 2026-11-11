"""Centralized structured JSON logging with request/workflow correlation and redaction."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
workflow_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "workflow_id", default=None
)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "app_secret_key",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "authorization",
        "cookie",
        "resume_text",
        "raw_text",
        "prompt_payload",
        "client_secret",
    }
)

_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }
)


def sanitize_log_value(value: Any, key: str | None = None) -> Any:
    """Recursively redact sensitive keys so credentials and raw resume payloads are not logged."""
    if key is not None and any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): sanitize_log_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_log_value(item) for item in value]
    return value


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line structured JSON with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "workflow_id": workflow_id_ctx.get(),
            "user_id": user_id_ctx.get(),
        }

        extra_fields: dict[str, Any] = {}
        for attr, val in record.__dict__.items():
            if attr not in _STANDARD_RECORD_ATTRS and not attr.startswith("_"):
                extra_fields[attr] = sanitize_log_value(val, key=attr)

        if extra_fields:
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root and application loggers for structured JSON output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for noisy_logger in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(
            logging.INFO if log_level.upper() == "DEBUG" else logging.WARNING
        )


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)

