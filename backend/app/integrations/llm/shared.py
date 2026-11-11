"""Shared LLM JSON extraction, secret scrubbing, and bounded retry utilities."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.exceptions import ExternalServiceError
from app.core.exceptions import RateLimitError as AppRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

_SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class LLMCompletionResult:
    """Structured LLM completion output with token telemetry."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    citations: tuple[str, ...] = field(default_factory=tuple)


class LLMClientProtocol(Protocol):
    """Protocol enabling deterministic mocked LLM responses in tests."""

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult: ...


class WebSearchLLMProtocol(Protocol):
    """Protocol for LLM web-search calls."""

    async def web_search_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> LLMCompletionResult: ...


class EmbeddingClientProtocol(Protocol):
    """Protocol enabling deterministic mocked text embeddings in tests."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True, slots=True)
class ToolCallingResult:
    """Multi-round function/tool calling response and telemetry."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    executed_tools: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class ToolCallingClientProtocol(Protocol):
    """Protocol enabling deterministic mocked tool-calling chat in tests."""

    async def complete_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_rounds: int = 6,
        max_tokens: int | None = None,
    ) -> ToolCallingResult: ...


def scrub_secret_tokens(detail: str) -> str:
    """Scrub potential API keys (OpenAI/Anthropic) from provider error strings."""
    if not detail:
        return ""
    return _SECRET_PATTERN.sub("[REDACTED]", detail)[:220]


def extract_safe_status_detail(exc: Any) -> str:
    """Safely extract and scrub error messages from provider HTTP exceptions."""
    body = getattr(exc, "body", None)
    detail = ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            detail = str(err.get("message") or "").strip()
        elif isinstance(err, str):
            detail = err.strip()
    if not detail:
        detail = str(getattr(exc, "message", "") or "").strip()
    return scrub_secret_tokens(detail)


def extract_json_object_text(raw_text: str) -> str:
    """Extract a clean JSON object string from raw text, markdown fences, or prose."""
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ""

    fence_match = _CODE_FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        candidate = cleaned[match.start() :]
        try:
            parsed_obj, end_idx = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed_obj, dict):
            return candidate[:end_idx]

    first_brace = cleaned.find("{")
    if first_brace != -1:
        return cleaned[first_brace:]

    return cleaned


def is_valid_json_object(raw_text: str) -> bool:
    """Return True when raw_text parses cleanly as a JSON object (dict)."""
    cleaned = extract_json_object_text(raw_text)
    if not cleaned:
        return False
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict)


async def execute_ai_with_retry(
    operation: Callable[[], Awaitable[Any]],
    *,
    max_retries: int,
    sleep_fn: Callable[[float], Awaitable[None]],
    rate_limit_exc: type[Exception],
    transient_excs: tuple[type[Exception], ...],
    status_exc: type[Exception],
    provider_label: str,
) -> Any:
    """Run an async LLM provider call with bounded exponential backoff on transient failures."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except rate_limit_exc as exc:
            last_exc = exc
            status_code = getattr(exc, "status_code", 429)
            err_lower = str(exc).lower()
            if (
                "insufficient_quota" in err_lower
                or "credit_balance_exhausted" in err_lower
                or "credit balance" in err_lower
            ):
                raise AppRateLimitError(
                    f"{provider_label} API credit balance exhausted or quota exceeded. "
                    f"Check {provider_label} billing limits."
                ) from exc
            if attempt < max_retries:
                await sleep_fn(0.5 * (2**attempt))
                continue
            raise AppRateLimitError(
                f"AI provider rate limit exceeded (status {status_code})."
            ) from exc
        except transient_excs as exc:
            last_exc = exc
            if attempt < max_retries:
                await sleep_fn(0.5 * (2**attempt))
                continue
            raise ExternalServiceError("AI provider request timed out or failed.") from exc
        except status_exc as exc:
            exc_status = int(getattr(exc, "status_code", 500) or 500)
            if exc_status >= 500 and attempt < max_retries:
                last_exc = exc
                await sleep_fn(0.5 * (2**attempt))
                continue
            detail = extract_safe_status_detail(exc)
            logger.warning(
                "AI provider status error",
                extra={"provider": provider_label, "status_code": exc_status, "detail": detail},
            )
            suffix = f": {detail}" if detail else "."
            raise ExternalServiceError(
                f"AI provider returned error status {exc_status}{suffix}"
            ) from exc

    raise ExternalServiceError("AI provider request failed after retries.") from last_exc
