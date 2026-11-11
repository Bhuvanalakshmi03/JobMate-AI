"""Centralized OpenAI chat, web-search, and embedding clients with retries and quotas."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
)
from app.core.exceptions import (
    RateLimitError as AppRateLimitError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_json_object_text(raw_text: str) -> str:
    """Extract a clean JSON object string from raw text, markdown fences, or prose."""
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return ""

    fence_match = _CODE_FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    if cleaned.startswith("{"):
        try:
            _, end_idx = json.JSONDecoder().raw_decode(cleaned)
            return cleaned[:end_idx]
        except json.JSONDecodeError:
            pass

    first_brace = cleaned.find("{")
    if first_brace != -1:
        candidate = cleaned[first_brace:]
        try:
            _, end_idx = json.JSONDecoder().raw_decode(candidate)
            return candidate[:end_idx]
        except json.JSONDecodeError:
            return candidate

    return cleaned


def _extract_safe_status_detail(exc: APIStatusError) -> str:
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
    if not detail:
        return ""
    scrubbed = _SECRET_PATTERN.sub("[REDACTED]", detail)
    return scrubbed[:220]


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
    """Protocol for OpenAI Responses API web-search calls."""

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


def _extract_citation_urls(response: Any) -> tuple[str, ...]:
    urls: list[str] = []
    seen: set[str] = set()
    for item in getattr(response, "output", []) or []:
        for content_part in getattr(item, "content", []) or []:
            for annotation in getattr(content_part, "annotations", []) or []:
                url = getattr(annotation, "url", None)
                if (
                    isinstance(url, str)
                    and url.startswith(("http://", "https://"))
                    and url not in seen
                ):
                    seen.add(url)
                    urls.append(url)
    return tuple(urls)


class OpenAIChatClient:
    """Centralized OpenAI adapter enforcing configured model, timeouts, and bounded retries."""

    def __init__(self, settings: Settings, max_retries: int = 2) -> None:
        self._api_key = settings.openai_api_key.strip()
        self._model = settings.openai_model
        self._embedding_model = settings.openai_embedding_model
        self._timeout = max(float(settings.openai_timeout_seconds), 75.0)
        self._default_max_tokens = settings.openai_max_tokens
        self._max_retries = max_retries
        self._client: AsyncOpenAI | None = (
            AsyncOpenAI(
                api_key=self._api_key,
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                max_retries=0,
            )
            if self._api_key
            else None
        )

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Configure it in .env to run AI features."
            )
        return self._client

    async def _execute_with_retry(self, operation: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await operation()
            except RateLimitError as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", 429)
                if "insufficient_quota" in str(exc).lower():
                    raise AppRateLimitError(
                        "AI provider quota exceeded. Check billing or usage limits."
                    ) from exc
                if attempt < self._max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise AppRateLimitError(
                    f"AI provider rate limit exceeded (status {status_code})."
                ) from exc
            except (APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise ExternalServiceError("AI provider request timed out or failed.") from exc
            except APIStatusError as exc:
                if exc.status_code >= 500 and attempt < self._max_retries:
                    last_exc = exc
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                detail = _extract_safe_status_detail(exc)
                logger.warning(
                    "AI provider status error",
                    extra={"status_code": exc.status_code, "detail": detail},
                )
                suffix = f": {detail}" if detail else "."
                raise ExternalServiceError(
                    f"AI provider returned error status {exc.status_code}{suffix}"
                ) from exc

        raise ExternalServiceError("AI provider request failed after retries.") from last_exc

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult:
        """Execute a JSON-formatted chat completion with bounded retry on transient failures."""
        client = self._require_client()
        token_budget = max_tokens or max(self._default_max_tokens, 4096)

        async def _call() -> Any:
            return await client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                max_tokens=token_budget,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        response = await self._execute_with_retry(_call)
        choice = response.choices[0] if response.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        if not content.strip():
            raise ExternalServiceError("AI provider returned an empty response.")

        usage = response.usage
        result = LLMCompletionResult(
            content=content,
            model=response.model or self._model,
            prompt_tokens=int(usage.prompt_tokens) if usage else 0,
            completion_tokens=int(usage.completion_tokens) if usage else 0,
            total_tokens=int(usage.total_tokens) if usage else 0,
        )
        logger.info(
            "LLM completion succeeded",
            extra={
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            },
        )
        return result

    async def web_search_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> LLMCompletionResult:
        """Execute OpenAI Responses API with live web_search tool for real-time discovery."""
        client = self._require_client()
        token_budget = max_output_tokens or max(self._default_max_tokens, 4096)

        async def _call() -> Any:
            # OpenAI Responses API rejects text.format=json_object alongside web_search tool;
            # structured JSON extraction is enforced downstream via extract_json_object_text.
            return await client.responses.create(
                model=self._model,
                instructions=system_prompt,
                input=user_prompt,
                tools=[{"type": "web_search"}],
                max_output_tokens=token_budget,
            )

        response = await self._execute_with_retry(_call)
        content = str(getattr(response, "output_text", "") or "").strip()
        if not content:
            raise ExternalServiceError("AI web search returned an empty response.")

        usage = getattr(response, "usage", None)
        citations = _extract_citation_urls(response)
        result = LLMCompletionResult(
            content=content,
            model=str(getattr(response, "model", None) or self._model),
            prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0) if usage else 0,
            completion_tokens=int(getattr(usage, "output_tokens", 0) or 0) if usage else 0,
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0) if usage else 0,
            citations=citations,
        )
        logger.info(
            "LLM web search succeeded",
            extra={
                "model": result.model,
                "total_tokens": result.total_tokens,
                "citation_count": len(citations),
            },
        )
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate dense semantic embeddings for normalized text inputs."""
        if not texts:
            return []
        client = self._require_client()
        cleaned = [t.strip()[:8000] or "empty" for t in texts]

        async def _call() -> Any:
            return await client.embeddings.create(
                model=self._embedding_model,
                input=cleaned,
            )

        response = await self._execute_with_retry(_call)
        vectors = [list(item.embedding) for item in sorted(response.data, key=lambda x: x.index)]
        logger.info(
            "Embedding generation succeeded",
            extra={"model": self._embedding_model, "count": len(vectors)},
        )
        return vectors
