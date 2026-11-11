"""RAG indexing and semantic retrieval service with strict per-user isolation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.chroma.store import RetrievedChunk, VectorChunk, VectorStoreProtocol
from app.integrations.openai.client import EmbeddingClientProtocol
from app.modules.documents.models import GeneratedDocument
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.rag.chunker import chunk_text, content_sha256, sanitize_untrusted_context
from app.modules.resume.models import ResumeFact

logger = get_logger(__name__)

CAREER_COLLECTION_NAME = "careerpilot_career_context"


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
        embedding_client: EmbeddingClientProtocol,
    ) -> None:
        self._session = session
        self._settings = settings
        self._vectors = vector_store
        self._embeddings = embedding_client
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)

    async def index_user_career_context(self, *, user_id: uuid.UUID) -> RAGSyncResult:
        """Index verified resume facts, career profile, and saved documents for one user."""
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
                    "embedding_model": self._settings.openai_embedding_model,
                }
                candidate_chunks.append((chunk_id, piece, metadata))

        if not candidate_chunks:
            return RAGSyncResult(
                indexed_chunks=0,
                skipped_duplicates=skipped_duplicates,
                source_counts=source_counts,
            )

        texts = [item[1] for item in candidate_chunks]
        embeddings = await self._embeddings.embed_texts(texts)

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

    async def retrieve_context(
        self,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve user-owned semantic context snippets with prompt-injection sanitization."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        try:
            query_embedding = (await self._embeddings.embed_texts([cleaned_query]))[0]
            raw_hits = await self._vectors.query(
                collection_name=CAREER_COLLECTION_NAME,
                user_id=str(user_id),
                query_embedding=query_embedding,
                top_k=top_k,
                source_types=source_types,
            )
        except ExternalServiceError as exc:
            logger.warning(
                "RAG vector retrieval unavailable; returning empty context",
                extra={"user_id": str(user_id), "error": str(exc)},
            )
            return []

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
