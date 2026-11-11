"""Unit tests for Anthropic Claude client adapter, provider factory, and lexical RAG fallback."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from anthropic import APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, ExternalServiceError
from app.core.exceptions import RateLimitError as AppRateLimitError
from app.integrations.chroma.store import InMemoryVectorStore
from app.integrations.claude.client import (
    ClaudeChatClient,
    _convert_openai_messages_to_claude,
    _convert_openai_tools_to_claude,
)
from app.integrations.llm.factory import (
    create_embedding_client,
    create_llm_client,
    get_web_search_source_provider,
)
from app.integrations.llm.shared import extract_json_object_text
from app.integrations.openai.client import OpenAIChatClient
from app.modules.authentication.models import User
from app.modules.profile.models import UserProfile, UserSkill
from app.modules.rag.service import RAGService
from app.modules.resume.schemas import ExtractedFactCandidate


async def test_claude_client_requires_api_key() -> None:
    client = ClaudeChatClient(Settings(llm_mode="claude", anthropic_api_key=""))
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")


async def test_claude_client_complete_json_and_web_search() -> None:
    client = ClaudeChatClient(
        Settings(
            llm_mode="claude",
            anthropic_api_key="sk-ant-usr-test-key",
            claude_model="claude-sonnet-5-5",
        ),
        max_retries=0,
    )
    assert client._client is not None
    captured_calls: list[dict[str, object]] = []

    async def fake_messages_create(**kwargs: object) -> object:
        captured_calls.append(dict(kwargs))
        if "tools" in kwargs:
            return SimpleNamespace(
                model="claude-sonnet-5-5",
                content=[
                    SimpleNamespace(
                        type="web_search_tool_result",
                        content=[
                            SimpleNamespace(url="https://careers.zoho.com/ai-intern"),
                        ],
                    ),
                    SimpleNamespace(
                        type="text",
                        text='{"jobs": [{"title": "AI Intern", "company": "Zoho"}]}',
                        citations=[
                            SimpleNamespace(url="https://careers.zoho.com/ai-intern"),
                            SimpleNamespace(url="https://jobs.freshworks.com/ml-role"),
                        ],
                    ),
                ],
                usage=SimpleNamespace(input_tokens=30, output_tokens=20),
            )
        return SimpleNamespace(
            model="claude-sonnet-5-5",
            content=[SimpleNamespace(type="text", text='```json\n{"ok": true}\n```')],
            usage=SimpleNamespace(input_tokens=15, output_tokens=10),
        )

    client._client.messages.create = fake_messages_create  # type: ignore[method-assign]

    json_res = await client.complete_json(system_prompt="Return facts", user_prompt="Resume text")
    assert json_res.content == '{"ok": true}'
    assert json_res.prompt_tokens == 15
    assert json_res.completion_tokens == 10
    assert json_res.total_tokens == 25

    search_res = await client.web_search_json(system_prompt="Find jobs", user_prompt="AI in India")
    assert search_res.citations == (
        "https://careers.zoho.com/ai-intern",
        "https://jobs.freshworks.com/ml-role",
    )
    assert len(captured_calls) == 2


async def test_claude_client_multi_round_tool_calling_and_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_sec: float) -> None:
        return None

    monkeypatch.setattr("app.integrations.claude.client.asyncio.sleep", no_sleep)
    client = ClaudeChatClient(
        Settings(llm_mode="claude", anthropic_api_key="sk-ant-usr-test-key"),
        max_retries=1,
    )
    assert client._client is not None

    round_counter = {"n": 0}
    recorded_payloads: list[dict[str, object]] = []

    async def fake_tool_create(**kwargs: object) -> object:
        round_counter["n"] += 1
        recorded_payloads.append(dict(kwargs))
        if round_counter["n"] == 1:
            return SimpleNamespace(
                model="claude-sonnet-5-5",
                content=[
                    SimpleNamespace(type="text", text="Checking applications..."),
                    SimpleNamespace(
                        type="tool_use",
                        id="toolu_1",
                        name="list_applications",
                        input={"limit": 5},
                    ),
                ],
                usage=SimpleNamespace(input_tokens=40, output_tokens=15),
            )
        return SimpleNamespace(
            model="claude-sonnet-5-5",
            content=[SimpleNamespace(type="text", text="You have 1 active application at Zoho.")],
            usage=SimpleNamespace(input_tokens=60, output_tokens=12),
        )

    async def fake_executor(name: str, args: dict[str, object]) -> str:
        assert name == "list_applications"
        assert args == {"limit": 5}
        return '{"items": [{"company": "Zoho"}]}'

    client._client.messages.create = fake_tool_create  # type: ignore[method-assign]
    result = await client.complete_with_tools(
        messages=[
            {"role": "system", "content": "You are JobMate AI."},
            {"role": "user", "content": "Show my applications"},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "list_applications",
                    "description": "List user applications.",
                    "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
                },
            }
        ],
        tool_executor=fake_executor,
    )
    assert "Zoho" in result.content
    assert result.total_tokens == 127
    assert len(result.executed_tools) == 1
    assert recorded_payloads[0]["system"] == "You are JobMate AI."
    assert recorded_payloads[1]["messages"][-1] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": '{"items": [{"company": "Zoho"}]}',
            }
        ],
    }

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(429, request=req)

    async def fake_credit_err(**_kwargs: object) -> object:
        raise RateLimitError(
            "Your credit balance is too low to access the Anthropic API.",
            response=resp,
            body={"error": {"message": "credit balance exhausted"}},
        )

    client._client.messages.create = fake_credit_err  # type: ignore[method-assign]
    with pytest.raises(AppRateLimitError, match="credit balance"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")

    async def fake_timeout(**_kwargs: object) -> object:
        raise APITimeoutError(request=req)

    client._client.messages.create = fake_timeout  # type: ignore[method-assign]
    with pytest.raises(ExternalServiceError, match="timed out"):
        await client.complete_json(system_prompt="sys", user_prompt="usr")


def test_openai_to_claude_converters_and_provider_factories() -> None:
    system, msgs = _convert_openai_messages_to_claude(
        [
            {"role": "system", "content": "System A"},
            {"role": "user", "content": "Hi"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "c1", "function": {"name": "search_jobs", "arguments": '{"q": "ml"}'}},
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": '{"total": 2}'},
        ]
    )
    assert system == "System A"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2] == {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "c1", "content": '{"total": 2}'}],
    }

    tools = _convert_openai_tools_to_claude(
        [{"type": "function", "function": {"name": "search_jobs", "description": "Find jobs"}}]
    )
    assert tools == [
        {
            "name": "search_jobs",
            "description": "Find jobs",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]

    claude_settings = Settings(llm_mode="claude", anthropic_api_key="sk-ant-usr-abc")
    openai_settings = Settings(llm_mode="openai", openai_api_key="sk-proj-abc")

    assert isinstance(create_llm_client(claude_settings), ClaudeChatClient)
    assert isinstance(create_llm_client(openai_settings), OpenAIChatClient)
    assert create_embedding_client(claude_settings) is None
    assert isinstance(create_embedding_client(openai_settings), OpenAIChatClient)
    assert get_web_search_source_provider(claude_settings) == "claude_web_search"
    assert get_web_search_source_provider(openai_settings) == "openai_web_search"


async def test_rag_lexical_fallback_works_in_claude_mode_without_embeddings(
    migrated_test_app: object,
) -> None:
    from fastapi import FastAPI

    assert isinstance(migrated_test_app, FastAPI)
    claude_settings = Settings(llm_mode="claude", anthropic_api_key="sk-ant-usr-test")

    async with migrated_test_app.router.lifespan_context(migrated_test_app):
        db_factory = migrated_test_app.state.db_session_factory
        async with db_factory() as session:
            assert isinstance(session, AsyncSession)
            user = User(
                email="claude.rag@example.edu",
                full_name="Claude Student",
                oauth_provider="google",
                oauth_subject="claude-rag-sub",
            )
            session.add(user)
            await session.flush()

            session.add(
                UserProfile(
                    user_id=user.id,
                    headline="FastAPI & PyTorch AI Engineer",
                    target_roles=["AI Engineer"],
                    preferred_locations=["Chennai"],
                )
            )
            session.add(
                UserSkill(
                    user_id=user.id,
                    name="PyTorch",
                    normalized_name="pytorch",
                    category="technical",
                    proficiency="advanced",
                    is_verified=True,
                )
            )
            await session.commit()

            rag = RAGService(
                session=session,
                settings=claude_settings,
                vector_store=InMemoryVectorStore(),
                embedding_client=None,
            )
            sync_res = await rag.index_user_career_context(user_id=user.id)
            assert sync_res.indexed_chunks == 0
            assert sync_res.source_counts["profile"] == 1

            hits = await rag.retrieve_context(user_id=user.id, query="PyTorch AI Engineer", top_k=3)
            assert len(hits) == 1
            assert "PyTorch" in hits[0].text


async def test_claude_truncation_auto_recovery_and_json_helpers() -> None:
    unclosed = '```json\n{"completeness_score": 88, "facts": []}'
    assert extract_json_object_text(unclosed) == '{"completeness_score": 88, "facts": []}'
    noisy = 'Note {not json} -> {"ok": true, "items": [1, 2]} tail'
    assert extract_json_object_text(noisy) == '{"ok": true, "items": [1, 2]}'

    fact = ExtractedFactCandidate(
        fact_type="award",  # type: ignore[arg-type]
        title="Dean's List",
        confidence=95,
    )
    assert fact.fact_type == "achievement"
    assert fact.confidence == 0.95

    client = ClaudeChatClient(
        Settings(llm_mode="claude", anthropic_api_key="sk-ant-usr-test", claude_max_tokens=8192),
        max_retries=0,
    )
    assert client._client is not None
    budgets: list[object] = []

    async def fake_truncated_then_valid(**kwargs: object) -> object:
        budgets.append(kwargs.get("max_tokens"))
        if len(budgets) == 1:
            return SimpleNamespace(
                model="claude-sonnet-5-5",
                stop_reason="max_tokens",
                content=[SimpleNamespace(type="text", text='{"incomplete": "cut off')],
                usage=SimpleNamespace(input_tokens=100, output_tokens=8192),
            )
        return SimpleNamespace(
            model="claude-sonnet-5-5",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text='{"ok": true, "facts": []}')],
            usage=SimpleNamespace(input_tokens=120, output_tokens=40),
        )

    client._client.messages.create = fake_truncated_then_valid  # type: ignore[method-assign]
    res = await client.complete_json(system_prompt="Extract", user_prompt="Resume", max_tokens=4096)
    assert budgets == [8192, 16384]
    assert res.content == '{"ok": true, "facts": []}'
    assert res.prompt_tokens == 220
    assert res.completion_tokens == 8232
