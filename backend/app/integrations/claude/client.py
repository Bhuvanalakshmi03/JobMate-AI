"""Centralized Anthropic Claude adapter supporting JSON, tool calling, and web search."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    RateLimitError,
)

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.integrations.llm.shared import (
    LLMCompletionResult,
    ToolCallingResult,
    execute_ai_with_retry,
    extract_json_object_text,
)
from app.integrations.openai.client import OpenAIChatClient

logger = get_logger(__name__)

_CLAUDE_WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}


def _convert_openai_tools_to_claude(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function-tool schemas into Anthropic tool definitions."""
    converted: list[dict[str, Any]] = []
    for item in tools:
        if item.get("type") == "function" and isinstance(item.get("function"), dict):
            fn = item["function"]
            converted.append(
                {
                    "name": str(fn.get("name") or ""),
                    "description": str(fn.get("description") or ""),
                    "input_schema": fn.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
            )
        elif "name" in item and "input_schema" in item:
            converted.append(dict(item))
    return converted


def _convert_openai_messages_to_claude(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Extract system prompts and map OpenAI chat/tool history to Anthropic format."""
    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []

    def _append_user_blocks(blocks: list[dict[str, Any]]) -> None:
        if converted and converted[-1]["role"] == "user":
            existing = converted[-1]["content"]
            if isinstance(existing, list):
                existing.extend(blocks)
                return
            converted[-1]["content"] = [
                {"type": "text", "text": str(existing)},
                *blocks,
            ]
            return
        converted.append({"role": "user", "content": blocks})

    for msg in messages:
        role = str(msg.get("role") or "").strip().lower()
        content = msg.get("content")
        if role == "system":
            if content is not None and str(content).strip():
                system_parts.append(str(content).strip())
            continue

        if role == "tool":
            tool_call_id = str(msg.get("tool_call_id") or "").strip()
            if not tool_call_id:
                continue
            _append_user_blocks(
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": str(content or "")[:8000],
                    }
                ]
            )
            continue

        if role == "assistant":
            blocks: list[dict[str, Any]] = []
            if content is not None and str(content).strip():
                blocks.append({"type": "text", "text": str(content)})
            for tc in list(msg.get("tool_calls") or []):
                fn = tc.get("function") or {}
                raw_args = fn.get("arguments")
                if isinstance(raw_args, dict):
                    parsed_input = raw_args
                else:
                    try:
                        decoded = json.loads(str(raw_args or "{}"))
                        parsed_input = decoded if isinstance(decoded, dict) else {}
                    except json.JSONDecodeError:
                        parsed_input = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": str(tc.get("id") or ""),
                        "name": str(fn.get("name") or ""),
                        "input": parsed_input,
                    }
                )
            if blocks:
                converted.append({"role": "assistant", "content": blocks})
            continue

        text_value = str(content or "").strip()
        if text_value:
            _append_user_blocks([{"type": "text", "text": text_value}])

    return "\n\n".join(system_parts), converted


def _extract_claude_text_and_citations(response: Any) -> tuple[str, tuple[str, ...]]:
    """Extract concatenated text and unique http(s) citation URLs from a Claude response."""
    text_parts: list[str] = []
    urls: list[str] = []
    seen_urls: set[str] = set()

    def _add_url(candidate: object) -> None:
        if (
            isinstance(candidate, str)
            and candidate.startswith(("http://", "https://"))
            and candidate not in seen_urls
        ):
            seen_urls.add(candidate)
            urls.append(candidate)

    for block in list(getattr(response, "content", None) or []):
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_val = getattr(block, "text", None)
            if isinstance(text_val, str) and text_val:
                text_parts.append(text_val)
            for citation in list(getattr(block, "citations", None) or []):
                _add_url(getattr(citation, "url", None))
        elif block_type == "web_search_tool_result":
            for result_item in list(getattr(block, "content", None) or []):
                _add_url(getattr(result_item, "url", None))

    return "\n".join(text_parts).strip(), tuple(urls)


def _extract_claude_tool_uses(response: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Serialize assistant content blocks and collect Claude tool_use invocations."""
    assistant_blocks: list[dict[str, Any]] = []
    tool_uses: list[dict[str, Any]] = []

    for block in list(getattr(response, "content", None) or []):
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_val = str(getattr(block, "text", "") or "")
            if text_val:
                assistant_blocks.append({"type": "text", "text": text_val})
        elif block_type == "tool_use":
            tool_id = str(getattr(block, "id", "") or "")
            tool_name = str(getattr(block, "name", "") or "")
            raw_input = getattr(block, "input", None)
            args = dict(raw_input) if isinstance(raw_input, dict) else {}
            tool_block = {
                "type": "tool_use",
                "id": tool_id,
                "name": tool_name,
                "input": args,
            }
            assistant_blocks.append(tool_block)
            tool_uses.append(tool_block)

    return assistant_blocks, tool_uses


class ClaudeChatClient:
    """Centralized Anthropic Claude adapter matching JobMate AI LLM protocols."""

    def __init__(self, settings: Settings, max_retries: int = 2) -> None:
        self._settings = settings
        self._api_key = settings.anthropic_api_key.strip()
        self._model = settings.claude_model
        self._timeout = max(float(settings.claude_timeout_seconds), 75.0)
        self._default_max_tokens = settings.claude_max_tokens
        self._max_retries = max_retries
        self._client: AsyncAnthropic | None = (
            AsyncAnthropic(
                api_key=self._api_key,
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                max_retries=0,
            )
            if self._api_key
            else None
        )

    def _require_client(self) -> AsyncAnthropic:
        if self._client is None:
            raise ConfigurationError(
                "ANTHROPIC_API_KEY is not configured. Configure it in .env when LLM_MODE=claude."
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
            provider_label="Anthropic Claude",
        )

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.1,
    ) -> LLMCompletionResult:
        """Execute a JSON-formatted Claude completion with bounded retries."""
        _ = temperature
        client = self._require_client()
        token_budget = max_tokens or max(self._default_max_tokens, 4096)
        json_system_prompt = (
            f"{system_prompt.strip()}\n\n"
            "CRITICAL OUTPUT FORMAT: Respond with ONLY a single valid JSON object. "
            "Do not include markdown code fences, commentary, or any text outside the JSON object."
        )

        async def _call() -> Any:
            return await client.messages.create(
                model=self._model,
                system=json_system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=token_budget,
            )

        response = await self._execute_with_retry(_call)
        raw_text, _ = _extract_claude_text_and_citations(response)
        cleaned_json = extract_json_object_text(raw_text)
        if not cleaned_json:
            raise ExternalServiceError("AI provider returned an empty response.")

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        result = LLMCompletionResult(
            content=cleaned_json,
            model=str(getattr(response, "model", None) or self._model),
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        logger.info(
            "Claude JSON completion succeeded",
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
        """Execute Anthropic Messages API with built-in web_search tool for live discovery."""
        client = self._require_client()
        token_budget = max_output_tokens or max(self._default_max_tokens, 4096)
        json_system_prompt = (
            f"{system_prompt.strip()}\n\n"
            "After completing web search calls, respond with ONLY a valid JSON object matching the "
            "requested schema without markdown fences."
        )

        async def _call() -> Any:
            return await client.messages.create(
                model=self._model,
                system=json_system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=cast(Any, [_CLAUDE_WEB_SEARCH_TOOL]),
                max_tokens=token_budget,
            )

        response = await self._execute_with_retry(_call)
        content, citations = _extract_claude_text_and_citations(response)
        if not content:
            raise ExternalServiceError("AI web search returned an empty response.")

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        result = LLMCompletionResult(
            content=content,
            model=str(getattr(response, "model", None) or self._model),
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            citations=citations,
        )
        logger.info(
            "Claude web search succeeded",
            extra={
                "model": result.model,
                "total_tokens": result.total_tokens,
                "citation_count": len(citations),
            },
        )
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Delegate embeddings to OpenAI only when hybrid embeddings are enabled."""
        if not texts:
            return []
        if self._settings.embeddings_configured:
            return await OpenAIChatClient(
                self._settings, max_retries=self._max_retries
            ).embed_texts(texts)
        raise ConfigurationError(
            "Anthropic Claude does not provide an embeddings API. Enable OpenAI or "
            "ENABLE_HYBRID_OPENAI_EMBEDDINGS=true for vector embeddings, or rely on lexical RAG."
        )

    async def complete_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[str]],
        max_rounds: int = 6,
        max_tokens: int | None = None,
    ) -> ToolCallingResult:
        """Execute a bounded multi-turn Claude tool-use loop preserving Co-Pilot semantics."""
        client = self._require_client()
        token_budget = max_tokens or max(self._default_max_tokens, 4096)
        system_prompt, working_messages = _convert_openai_messages_to_claude(messages)
        claude_tools = _convert_openai_tools_to_claude(tools)
        executed_tools: list[dict[str, Any]] = []
        total_prompt = 0
        total_completion = 0
        model_used = self._model

        for _ in range(max(1, max_rounds)):

            async def _call() -> Any:
                return await client.messages.create(
                    model=self._model,
                    system=system_prompt,
                    messages=cast(Any, working_messages),
                    tools=cast(Any, claude_tools),
                    max_tokens=token_budget,
                )

            response = await self._execute_with_retry(_call)
            model_used = str(getattr(response, "model", None) or self._model)
            usage = getattr(response, "usage", None)
            if usage:
                total_prompt += int(getattr(usage, "input_tokens", 0) or 0)
                total_completion += int(getattr(usage, "output_tokens", 0) or 0)

            assistant_blocks, tool_uses = _extract_claude_tool_uses(response)
            if not tool_uses:
                final_text, _ = _extract_claude_text_and_citations(response)
                return ToolCallingResult(
                    content=final_text or "Completed your request.",
                    model=model_used,
                    prompt_tokens=total_prompt,
                    completion_tokens=total_completion,
                    total_tokens=total_prompt + total_completion,
                    executed_tools=tuple(executed_tools),
                )

            working_messages.append({"role": "assistant", "content": assistant_blocks})
            tool_result_blocks: list[dict[str, Any]] = []

            for call in tool_uses:
                tool_name = str(call["name"])
                parsed_args = dict(call["input"])
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
                tool_result_block: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": str(call["id"]),
                    "content": tool_output[:8000],
                }
                if status == "error":
                    tool_result_block["is_error"] = True
                tool_result_blocks.append(tool_result_block)

            working_messages.append({"role": "user", "content": tool_result_blocks})

        async def _final_call() -> Any:
            return await client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=cast(Any, working_messages),
                max_tokens=token_budget,
            )

        final_resp = await self._execute_with_retry(_final_call)
        final_usage = getattr(final_resp, "usage", None)
        if final_usage:
            total_prompt += int(getattr(final_usage, "input_tokens", 0) or 0)
            total_completion += int(getattr(final_usage, "output_tokens", 0) or 0)
        final_content, _ = _extract_claude_text_and_citations(final_resp)
        return ToolCallingResult(
            content=final_content or "Completed requested actions.",
            model=str(getattr(final_resp, "model", None) or model_used),
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            executed_tools=tuple(executed_tools),
        )
