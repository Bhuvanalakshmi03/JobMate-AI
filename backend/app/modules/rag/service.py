"""RAG indexing and semantic retrieval service with strict per-user isolation."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, ExternalServiceError, RateLimitError
from app.core.logging import get_logger
from app.integrations.chroma.store import RetrievedChunk, VectorChunk, VectorStoreProtocol
from app.integrations.openai.client import EmbeddingClientProtocol
from app.modules.documents.models import GeneratedDocument
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.rag.chunker import chunk_text, content_sha256, sanitize_untrusted_context
from app.modules.resume.models import ResumeFact

logger = get_logger(__name__)

CAREER_COLLECTION_NAME = "jobmate_career_context"


@dataclass(frozen=True, slots=True)
class RAGSyncResult:
    """Telemetry returned after indexing user-owned career artifacts."""

    indexed_chunks: int
    skipped_duplicates: int
    source_counts: dict[str, int]


class RAGService:
    """Indexes verified student career records and retrieves user-isolated context."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        vector_store: VectorStoreProtocol,
        embedding_client: EmbeddingClientProtocol | None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._vectors = vector_store
        self._embeddings = embedding_client
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)

    async def _collect_candidate_chunks(
        self, *, user_id: uuid.UUID
    ) -> tuple[list[tuple[str, str, dict[str, str]]], int, dict[str, int]]:
        profile = await self._profiles.get_by_user_id(user_id)
        skills = await self._skills.list_by_user_id(user_id)
        facts = list(
            (
                await self._session.scalars(
                    select(ResumeFact).where(
                        ResumeFact.user_id == user_id,
                        ResumeFact.is_verified.is_(True),
                        ResumeFact.verification_status != "rejected",
                    )
                )
            ).all()
        )
        documents = list(
            (
                await self._session.scalars(
                    select(GeneratedDocument).where(GeneratedDocument.user_id == user_id)
                )
            ).all()
        )

        raw_records: list[tuple[str, str, str, str]] = []
        source_counts: dict[str, int] = {"profile": 0, "resume_fact": 0, "document": 0}

        if profile is not None or skills:
            skill_names = ", ".join(s.name for s in skills)
            profile_parts = [
                f"Target Roles: {', '.join(profile.target_roles)}"
                if profile and profile.target_roles
                else "",
                f"Preferred Locations: {', '.join(profile.preferred_locations)}"
                if profile and profile.preferred_locations
                else "",
                f"Headline: {profile.headline}" if profile and profile.headline else "",
                f"Summary: {profile.summary}" if profile and profile.summary else "",
                f"Verified Skills: {skill_names}" if skill_names else "",
            ]
            profile_text = "\n".join(part for part in profile_parts if part)
            if profile_text:
                raw_records.append(("profile", str(user_id), "Career Profile", profile_text))
                source_counts["profile"] += 1

        for fact in facts:
            fact_text = " — ".join(
                part
                for part in (
                    f"[{fact.fact_type.upper()}] {fact.title}",
                    fact.organization,
                    fact.description,
                    f"Evidence: {fact.evidence_excerpt}" if fact.evidence_excerpt else None,
                )
                if part and part.strip()
            )
            raw_records.append(("resume_fact", str(fact.id), fact.title, fact_text))
            source_counts["resume_fact"] += 1

        for doc in documents:
            raw_records.append(
                ("document", str(doc.id), f"{doc.title} (v{doc.version})", doc.content_markdown)
            )
            source_counts["document"] += 1

        candidate_chunks: list[tuple[str, str, dict[str, str]]] = []
        seen_hashes: set[str] = set()
        skipped_duplicates = 0
        embedding_label = (
            self._settings.openai_embedding_model
            if self._embeddings is not None
            else "lexical_fallback"
        )

        for source_type, source_id, label, body in raw_records:
            for idx, piece in enumerate(chunk_text(body)):
                c_hash = content_sha256(f"{source_type}:{piece}")
                if c_hash in seen_hashes:
                    skipped_duplicates += 1
                    continue
                seen_hashes.add(c_hash)
                chunk_id = f"{user_id}:{source_type}:{source_id}:{idx}:{c_hash[:12]}"
                metadata = {
                    "user_id": str(user_id),
                    "source_type": source_type,
                    "source_id": source_id,
                    "label": label[:200],
                    "content_hash": c_hash,
                    "embedding_model": embedding_label,
                }
                candidate_chunks.append((chunk_id, piece, metadata))

        return candidate_chunks, skipped_duplicates, source_counts

    async def index_user_career_context(self, *, user_id: uuid.UUID) -> RAGSyncResult:
        """Index verified resume facts, career profile, and saved documents for one user."""
        candidate_chunks, skipped_duplicates, source_counts = (
            await self._collect_candidate_chunks(user_id=user_id)
        )
        if not candidate_chunks or self._embeddings is None:
            return RAGSyncResult(
                indexed_chunks=0,
                skipped_duplicates=skipped_duplicates,
                source_counts=source_counts,
            )

        texts = [item[1] for item in candidate_chunks]
        try:
            embeddings = await self._embeddings.embed_texts(texts)
        except (ExternalServiceError, ConfigurationError, RateLimitError) as exc:
            logger.warning(
                "RAG embedding generation unavailable; skipping vector upsert",
                extra={"user_id": str(user_id), "exception_class": exc.__class__.__name__},
            )
            return RAGSyncResult(
                indexed_chunks=0,
                skipped_duplicates=skipped_duplicates,
                source_counts=source_counts,
            )

        vector_chunks = [
            VectorChunk(
                chunk_id=chunk_id,
                text=text,
                embedding=embedding,
                metadata=metadata,
            )
            for (chunk_id, text, metadata), embedding in zip(
                candidate_chunks, embeddings, strict=True
            )
        ]

        await self._vectors.upsert_chunks(
            collection_name=CAREER_COLLECTION_NAME,
            chunks=vector_chunks,
        )
        return RAGSyncResult(
            indexed_chunks=len(vector_chunks),
            skipped_duplicates=skipped_duplicates,
            source_counts=source_counts,
        )

    async def _lexical_retrieve(
        self,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int,
        source_types: list[str] | None,
    ) -> list[RetrievedChunk]:
        candidate_chunks, _, _ = await self._collect_candidate_chunks(user_id=user_id)
        if source_types:
            allowed = set(source_types)
            candidate_chunks = [
                item for item in candidate_chunks if item[2].get("source_type") in allowed
            ]
        query_terms = {tok for tok in re.findall(r"[a-z0-9]{2,}", query.lower())}
        scored: list[tuple[float, str, str, dict[str, str]]] = []
        for chunk_id, piece, metadata in candidate_chunks:
            piece_terms = set(re.findall(r"[a-z0-9]{2,}", piece.lower()))
            overlap = len(query_terms & piece_terms)
            base_score = overlap / max(1, len(query_terms)) if query_terms else 0.1
            scored.append((round(min(1.0, base_score), 4), chunk_id, piece, metadata))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [
            RetrievedChunk(
                chunk_id=chunk_id,
                text=sanitize_untrusted_context(piece),
                score=score,
                metadata=metadata,
            )
            for score, chunk_id, piece, metadata in scored[:top_k]
        ]

    async def retrieve_context(
        self,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve user-owned career snippets via dense vectors or lexical DB fallback."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        if self._embeddings is None:
            return await self._lexical_retrieve(
                user_id=user_id, query=cleaned_query, top_k=top_k, source_types=source_types
            )

        try:
            query_embedding = (await self._embeddings.embed_texts([cleaned_query]))[0]
            raw_hits = await self._vectors.query(
                collection_name=CAREER_COLLECTION_NAME,
                user_id=str(user_id),
                query_embedding=query_embedding,
                top_k=top_k,
                source_types=source_types,
            )
        except (ExternalServiceError, ConfigurationError, RateLimitError) as exc:
            logger.warning(
                "RAG vector retrieval unavailable; using lexical career fallback",
                extra={"user_id": str(user_id), "error": str(exc)},
            )
            return await self._lexical_retrieve(
                user_id=user_id, query=cleaned_query, top_k=top_k, source_types=source_types
            )

        validated: list[RetrievedChunk] = []
        for hit in raw_hits:
            if str(hit.metadata.get("user_id", "")) != str(user_id):
                continue
            validated.append(
                RetrievedChunk(
                    chunk_id=hit.chunk_id,
                    text=sanitize_untrusted_context(hit.text),
                    score=hit.score,
                    metadata=hit.metadata,
                )
            )
        return validated

    async def delete_user_source(
        self,
        *,
        user_id: uuid.UUID,
        source_id: str | None = None,
    ) -> None:
        """Remove one source document or all user chunks from vector storage."""
        await self._vectors.delete_by_filter(
            collection_name=CAREER_COLLECTION_NAME,
            user_id=str(user_id),
            source_id=source_id,
        )
