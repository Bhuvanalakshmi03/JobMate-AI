"""Dedicated vector-store abstraction with ChromaDB v2 HTTP and in-memory implementations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class VectorChunk:
    """Normalized document chunk prepared for semantic indexing."""

    chunk_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Retrieved semantic context chunk paired with ownership-validated metadata."""

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStoreProtocol(Protocol):
    """Abstract vector database contract decoupling RAG logic from ChromaDB."""

    async def heartbeat(self) -> bool: ...

    async def upsert_chunks(
        self,
        *,
        collection_name: str,
        chunks: list[VectorChunk],
    ) -> int: ...

    async def query(
        self,
        *,
        collection_name: str,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]: ...

    async def delete_by_filter(
        self,
        *,
        collection_name: str,
        user_id: str,
        source_id: str | None = None,
    ) -> None: ...


class ChromaVectorStore:
    """Async ChromaDB HTTP v2 REST API adapter with strict user-scoped filtering."""

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = settings.chroma_url.rstrip("/")
        self._api_key = settings.chroma_api_key.strip()
        self._tenant = settings.chroma_tenant.strip() or "default_tenant"
        self._database = settings.chroma_database.strip() or "default_database"
        self._timeout = timeout_seconds
        self._transport = transport
        self._collection_ids: dict[str, str] = {}

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-chroma-token"] = self._api_key
        return headers

    def _db_prefix(self) -> str:
        return f"/api/v2/tenants/{self._tenant}/databases/{self._database}"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers(),
            timeout=self._timeout,
            transport=self._transport,
        )

    async def heartbeat(self) -> bool:
        try:
            async with self._client() as client:
                response = await client.get("/api/v2/heartbeat")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def _ensure_collection_id(
        self,
        client: httpx.AsyncClient,
        collection_name: str,
    ) -> str:
        cached = self._collection_ids.get(collection_name)
        if cached:
            return cached

        response = await client.post(
            f"{self._db_prefix()}/collections",
            json={
                "name": collection_name,
                "get_or_create": True,
                "metadata": {"hnsw:space": "cosine"},
            },
        )
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Vector store failed to initialize collection ({response.status_code})."
            )
        data = response.json()
        collection_id = str(data.get("id", "")).strip()
        if not collection_id:
            raise ExternalServiceError("Vector store returned an invalid collection identifier.")
        self._collection_ids[collection_name] = collection_id
        return collection_id

    async def upsert_chunks(
        self,
        *,
        collection_name: str,
        chunks: list[VectorChunk],
    ) -> int:
        if not chunks:
            return 0
        try:
            async with self._client() as client:
                collection_id = await self._ensure_collection_id(client, collection_name)
                response = await client.post(
                    f"{self._db_prefix()}/collections/{collection_id}/upsert",
                    json={
                        "ids": [c.chunk_id for c in chunks],
                        "embeddings": [c.embedding for c in chunks],
                        "documents": [c.text for c in chunks],
                        "metadatas": [c.metadata for c in chunks],
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("Chroma upsert request failed", extra={"error": str(exc)})
            raise ExternalServiceError("Vector store request failed during indexing.") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Vector store upsert failed ({response.status_code})."
            )
        return len(chunks)

    async def query(
        self,
        *,
        collection_name: str,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        where_clause: dict[str, Any] = {"user_id": user_id}
        if source_types:
            where_clause = {
                "$and": [
                    {"user_id": user_id},
                    {"source_type": {"$in": source_types}},
                ]
            }

        try:
            async with self._client() as client:
                collection_id = await self._ensure_collection_id(client, collection_name)
                response = await client.post(
                    f"{self._db_prefix()}/collections/{collection_id}/query",
                    json={
                        "query_embeddings": [query_embedding],
                        "n_results": max(1, min(top_k, 25)),
                        "where": where_clause,
                        "include": ["documents", "metadatas", "distances"],
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("Chroma query request failed", extra={"error": str(exc)})
            raise ExternalServiceError("Vector store query failed.") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Vector store query returned error ({response.status_code})."
            )

        payload = response.json()
        ids_batch = (payload.get("ids") or [[]])[0]
        docs_batch = (payload.get("documents") or [[]])[0]
        metas_batch = (payload.get("metadatas") or [[]])[0]
        dists_batch = (payload.get("distances") or [[]])[0]

        results: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(ids_batch):
            metadata = metas_batch[idx] if idx < len(metas_batch) and metas_batch[idx] else {}
            if str(metadata.get("user_id", "")) != user_id:
                continue
            text = str(docs_batch[idx]) if idx < len(docs_batch) and docs_batch[idx] else ""
            raw_distance = (
                dists_batch[idx]
                if idx < len(dists_batch) and dists_batch[idx] is not None
                else 1.0
            )
            distance = float(raw_distance)
            similarity = max(0.0, min(1.0, 1.0 - distance))
            results.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    text=text,
                    score=round(similarity, 4),
                    metadata=dict(metadata),
                )
            )
        return results

    async def delete_by_filter(
        self,
        *,
        collection_name: str,
        user_id: str,
        source_id: str | None = None,
    ) -> None:
        where_clause: dict[str, Any] = {"user_id": user_id}
        if source_id is not None:
            where_clause = {"$and": [{"user_id": user_id}, {"source_id": source_id}]}

        try:
            async with self._client() as client:
                collection_id = await self._ensure_collection_id(client, collection_name)
                response = await client.post(
                    f"{self._db_prefix()}/collections/{collection_id}/delete",
                    json={"where": where_clause},
                )
        except httpx.HTTPError as exc:
            logger.warning("Chroma delete request failed", extra={"error": str(exc)})
            raise ExternalServiceError("Vector store deletion failed.") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Vector store deletion returned error ({response.status_code})."
            )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0.0 or norm_r == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_l * norm_r)))


class InMemoryVectorStore:
    """In-memory VectorStoreProtocol implementation for isolated unit tests and fallbacks."""

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, VectorChunk]] = {}

    async def heartbeat(self) -> bool:
        return True

    async def upsert_chunks(
        self,
        *,
        collection_name: str,
        chunks: list[VectorChunk],
    ) -> int:
        bucket = self._collections.setdefault(collection_name, {})
        for chunk in chunks:
            bucket[chunk.chunk_id] = chunk
        return len(chunks)

    async def query(
        self,
        *,
        collection_name: str,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        bucket = self._collections.get(collection_name, {})
        scored: list[RetrievedChunk] = []
        for chunk in bucket.values():
            if str(chunk.metadata.get("user_id", "")) != user_id:
                continue
            if source_types and str(chunk.metadata.get("source_type", "")) not in source_types:
                continue
            sim = _cosine_similarity(query_embedding, chunk.embedding)
            scored.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=round(sim, 4),
                    metadata=dict(chunk.metadata),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, top_k)]

    async def delete_by_filter(
        self,
        *,
        collection_name: str,
        user_id: str,
        source_id: str | None = None,
    ) -> None:
        bucket = self._collections.get(collection_name)
        if not bucket:
            return
        to_delete = [
            cid
            for cid, chunk in bucket.items()
            if str(chunk.metadata.get("user_id", "")) == user_id
            and (source_id is None or str(chunk.metadata.get("source_id", "")) == source_id)
        ]
        for cid in to_delete:
            bucket.pop(cid, None)


def create_vector_store(settings: Settings) -> VectorStoreProtocol:
    """Construct configured vector store adapter (ChromaDB v2 HTTP or in-memory fallback)."""
    if settings.chroma_url.strip():
        return ChromaVectorStore(settings)
    return InMemoryVectorStore()
