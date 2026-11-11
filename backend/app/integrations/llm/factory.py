"""Centralized provider factory routing AI operations based on Settings.llm_mode."""

from __future__ import annotations

from app.core.config import Settings
from app.integrations.claude.client import ClaudeChatClient
from app.integrations.job_search.openai_web_search import (
    JobSearchProviderProtocol,
    OpenAIWebSearchJobProvider,
)
from app.integrations.openai.client import EmbeddingClientProtocol, OpenAIChatClient

AIChatClient = OpenAIChatClient | ClaudeChatClient


def create_llm_client(settings: Settings) -> AIChatClient:
    """Return the configured LLM client (OpenAI or Anthropic Claude) based on LLM_MODE."""
    if settings.is_claude_mode:
        return ClaudeChatClient(settings)
    return OpenAIChatClient(settings)


def create_embedding_client(settings: Settings) -> EmbeddingClientProtocol | None:
    """Return dense embedding client when OpenAI embeddings are configured, else None."""
    if settings.embeddings_configured:
        return OpenAIChatClient(settings)
    return None


def get_web_search_source_provider(settings: Settings) -> str:
    """Return normalized job source provider label for the active LLM mode."""
    return "claude_web_search" if settings.is_claude_mode else "openai_web_search"


def create_job_search_provider(
    settings: Settings,
    *,
    llm_client: AIChatClient | None = None,
) -> JobSearchProviderProtocol:
    """Build web-search job discovery adapter backed by the active LLM_MODE provider."""
    client = llm_client or create_llm_client(settings)
    return OpenAIWebSearchJobProvider(
        client,
        source_provider=get_web_search_source_provider(settings),
    )
