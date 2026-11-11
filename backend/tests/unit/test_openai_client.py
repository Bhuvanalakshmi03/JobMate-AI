"""Unit tests for centralized OpenAI client wrapper."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, ExternalServiceError
from app.core.exceptions import RateLimitError as AppRateLimitError
from app.integrations.openai.client import OpenAIChatClient


async def test_openai_client_requires_api_key() -> None:
    client = OpenAIChatClient(Settings(openai_api_key=""))
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")


async def test_openai_client_returns_completion_and_usage() -> None:
    client = OpenAIChatClient(Settings(openai_api_key="sk-test-key"), max_retries=1)

    async def fake_create(**_kwargs: object) -> object:
        return SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    assert client._client is not None
    client._client.chat.completions.create = fake_create  # type: ignore[method-assign]

    res = await client.complete_json(system_prompt="sys", user_prompt="usr")
    assert res.content == '{"ok": true}'
    assert res.total_tokens == 15


async def test_openai_client_handles_quota_and_timeout_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_sec: float) -> None:
        return None

    monkeypatch.setattr("app.integrations.openai.client.asyncio.sleep", no_sleep)
    client = OpenAIChatClient(Settings(openai_api_key="sk-test-key"), max_retries=1)
    assert client._client is not None

    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(429, request=req)

    async def fake_quota(**_kwargs: object) -> object:
        raise RateLimitError(
            "You exceeded your current quota, insufficient_quota",
            response=resp,
            body={"error": {"code": "insufficient_quota"}},
        )

    client._client.chat.completions.create = fake_quota  # type: ignore[method-assign]
    with pytest.raises(AppRateLimitError, match="quota exceeded"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")

    async def fake_timeout(**_kwargs: object) -> object:
        raise APITimeoutError(request=req)

    client._client.chat.completions.create = fake_timeout  # type: ignore[method-assign]
    with pytest.raises(ExternalServiceError, match="timed out"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")


async def test_openai_client_web_search_and_embeddings() -> None:
    client = OpenAIChatClient(Settings(openai_api_key="sk-test-key"), max_retries=0)
    assert client._client is not None

    async def fake_responses_create(**_kwargs: object) -> object:
        return SimpleNamespace(
            model="gpt-4o-mini",
            output_text='{"jobs": []}',
            usage=SimpleNamespace(input_tokens=20, output_tokens=30, total_tokens=50),
            output=[
                SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            annotations=[SimpleNamespace(url="https://careers.example.io/job/1")]
                        )
                    ]
                )
            ],
        )

    async def fake_embeddings_create(**_kwargs: object) -> object:
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.2, 0.8]),
                SimpleNamespace(index=0, embedding=[0.9, 0.1]),
            ]
        )

    client._client.responses.create = fake_responses_create  # type: ignore[method-assign]
    client._client.embeddings.create = fake_embeddings_create  # type: ignore[method-assign]

    search_res = await client.web_search_json(system_prompt="sys", user_prompt="find jobs")
    assert search_res.content == '{"jobs": []}'
    assert search_res.citations == ("https://careers.example.io/job/1",)

    vectors = await client.embed_texts(["first", "second"])
    assert vectors == [[0.9, 0.1], [0.2, 0.8]]
