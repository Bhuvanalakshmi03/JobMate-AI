"""Centralized application exceptions and safe FastAPI error handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class AppError(Exception):
    """Base application exception mapped to a deterministic JSON error response."""

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected application error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ConfigurationError(AppError):
    code = "CONFIGURATION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Application configuration is invalid."


class AuthenticationError(AppError):
    code = "AUTHENTICATION_FAILED"
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication is required or credentials are invalid."


class AuthorizationError(AppError):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "The requested resource was not found."


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_message = "The submitted request data is invalid."


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT
    default_message = "The requested operation conflicts with existing state."


class RateLimitError(AppError):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "Rate limit exceeded. Please retry later."


class ExternalServiceError(AppError):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "An upstream external service request failed."


class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "Database service is temporarily unavailable."


def build_error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Construct consistent error envelope without exposing internal stack traces."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id or request_id_ctx.get(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach centralized exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None) or request_id_ctx.get()
        logger.warning(
            "Application error handled",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "request_id": req_id,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=req_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None) or request_id_ctx.get()
        sanitized_errors = [
            {
                "loc": list(err.get("loc", ())),
                "msg": str(err.get("msg", "Invalid input")),
                "type": str(err.get("type", "value_error")),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=build_error_payload(
                code="REQUEST_VALIDATION_ERROR",
                message="Request validation failed.",
                details=sanitized_errors,
                request_id=req_id,
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None) or request_id_ctx.get()
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail) if exc.detail else "HTTP error",
                request_id=req_id,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None) or request_id_ctx.get()
        logger.exception(
            "Unhandled server exception",
            extra={
                "path": str(request.url.path),
                "exception_class": exc.__class__.__name__,
                "request_id": req_id,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_payload(
                code="INTERNAL_SERVER_ERROR",
                message="An internal error occurred. Please retry or contact support.",
                request_id=req_id,
            ),
        )

