"""Centralized OpenAI chat completion client with timeouts, token limits, and retries."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class LLMCompletionResult:
    """Structured LLM completion output with token telemetry."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


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


class OpenAIChatClient:
    """Centralized OpenAI adapter enforcing configured model, timeouts, and bounded retries."""

    def __init__(self, settings: Settings, max_retries: int = 2) -> None:
        self._api_key = settings.openai_api_key.strip()
        self._model = settings.openai_model
        self._timeout = settings.openai_timeout_seconds
        self._default_max_tokens = settings.openai_max_tokens
        self._max_retries = max_retries
        self._client: AsyncOpenAI | None = (
            AsyncOpenAI(api_key=self._api_key, timeout=float(self._timeout), max_retries=0)
            if self._api_key
            else None
        )

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult:
        """Execute a JSON-formatted chat completion with bounded retry on transient failures."""
        if self._client is None:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Configure it in .env to run AI analysis."
            )

        token_budget = max_tokens or self._default_max_tokens
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=temperature,
                    max_tokens=token_budget,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
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

            except RateLimitError as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", 429)
                body_str = str(exc).lower()
                if "insufficient_quota" in body_str:
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
                raise ExternalServiceError(
                    f"AI provider returned error status {exc.status_code}."
                ) from exc

        raise ExternalServiceError("AI provider request failed after retries.") from last_exc
