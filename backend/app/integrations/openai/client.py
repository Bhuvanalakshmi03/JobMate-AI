"""Centralized OpenAI chat, web-search, and embedding clients with retries and quotas."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
)
from app.core.logging import get_logger
from app.integrations.llm.shared import (
    EmbeddingClientProtocol as EmbeddingClientProtocol,
)
from app.integrations.llm.shared import (
    LLMClientProtocol as LLMClientProtocol,
)
from app.integrations.llm.shared import (
    LLMCompletionResult as LLMCompletionResult,
)
from app.integrations.llm.shared import (
    ToolCallingClientProtocol as ToolCallingClientProtocol,
)
from app.integrations.llm.shared import (
    ToolCallingResult as ToolCallingResult,
)
from app.integrations.llm.shared import (
    WebSearchLLMProtocol as WebSearchLLMProtocol,
)
from app.integrations.llm.shared import (
    execute_ai_with_retry,
)
from app.integrations.llm.shared import (
    extract_json_object_text as extract_json_object_text,
)

logger = get_logger(__name__)


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

    async def _execute_with_retry(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        return await execute_ai_with_retry(
            operation,
            max_retries=self._max_retries,
            sleep_fn=asyncio.sleep,
            rate_limit_exc=RateLimitError,
            transient_excs=(APITimeoutError, APIConnectionError),
            status_exc=APIStatusError,
            provider_label="OpenAI",
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

    async def complete_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_rounds: int = 6,
        max_tokens: int | None = None,
    ) -> ToolCallingResult:
        """Execute a bounded multi-turn OpenAI function-calling conversation loop."""
        client = self._require_client()
        token_budget = max_tokens or max(self._default_max_tokens, 4096)
        working_messages: list[dict[str, Any]] = [dict(msg) for msg in messages]
        executed_tools: list[dict[str, Any]] = []
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        model_used = self._model

        for _ in range(max(1, max_rounds)):
            async def _call() -> Any:
                return await client.chat.completions.create(
                    model=self._model,
                    messages=cast(Any, working_messages),
                    tools=cast(Any, tools),
                    tool_choice="auto",
                    max_tokens=token_budget,
                    temperature=0.2,
                )

            response = await self._execute_with_retry(_call)
            model_used = str(getattr(response, "model", None) or self._model)
            usage = getattr(response, "usage", None)
            if usage:
                total_prompt += int(getattr(usage, "prompt_tokens", 0) or 0)
                total_completion += int(getattr(usage, "completion_tokens", 0) or 0)
                total_tokens += int(getattr(usage, "total_tokens", 0) or 0)

            choice = response.choices[0] if response.choices else None
            msg = choice.message if choice else None
            raw_tool_calls = list(getattr(msg, "tool_calls", None) or []) if msg else []

            if not raw_tool_calls:
                final_text = str(getattr(msg, "content", "") or "").strip() if msg else ""
                if not final_text:
                    final_text = "Completed your request."
                return ToolCallingResult(
                    content=final_text,
                    model=model_used,
                    prompt_tokens=total_prompt,
                    completion_tokens=total_completion,
                    total_tokens=total_tokens,
                    executed_tools=tuple(executed_tools),
                )

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": getattr(msg, "content", None),
                "tool_calls": [
                    {
                        "id": str(tc.id),
                        "type": "function",
                        "function": {
                            "name": str(tc.function.name),
                            "arguments": str(tc.function.arguments or "{}"),
                        },
                    }
                    for tc in raw_tool_calls
                ],
            }
            working_messages.append(assistant_msg)

            for tc in raw_tool_calls:
                tool_name = str(tc.function.name)
                raw_args = str(tc.function.arguments or "{}")
                try:
                    parsed_args = json.loads(raw_args)
                    if not isinstance(parsed_args, dict):
                        parsed_args = {}
                except json.JSONDecodeError:
                    parsed_args = {}

                status = "completed"
                try:
                    tool_output = await tool_executor(tool_name, parsed_args)
                except Exception as exc:
                    status = "error"
                    tool_output = json.dumps({"error": str(exc) or exc.__class__.__name__})

                executed_tools.append(
                    {
                        "tool_name": tool_name,
                        "arguments": parsed_args,
                        "status": status,
                        "result_preview": tool_output[:320],
                    }
                )
                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tc.id),
                        "content": tool_output[:8000],
                    }
                )

        # Final synthesis pass without further tool calls if max_rounds reached cleanly.
        async def _final_call() -> Any:
            return await client.chat.completions.create(
                model=self._model,
                messages=cast(Any, working_messages),
                max_tokens=token_budget,
                temperature=0.2,
            )

        final_resp = await self._execute_with_retry(_final_call)
        final_usage = getattr(final_resp, "usage", None)
        if final_usage:
            total_prompt += int(getattr(final_usage, "prompt_tokens", 0) or 0)
            total_completion += int(getattr(final_usage, "completion_tokens", 0) or 0)
            total_tokens += int(getattr(final_usage, "total_tokens", 0) or 0)
        final_choice = final_resp.choices[0] if final_resp.choices else None
        final_content = (
            str(getattr(final_choice.message, "content", "") or "").strip()
            if final_choice and final_choice.message
            else "Completed requested actions."
        )
        return ToolCallingResult(
            content=final_content,
            model=model_used,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_tokens,
            executed_tools=tuple(executed_tools),
        )
