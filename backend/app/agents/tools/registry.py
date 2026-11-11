"""User-scoped tool registry preventing unrestricted DB access or cross-user leakage."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.prompts.advisory import CAREER_ADVISORY_SYSTEM_PROMPT
from app.agents.prompts.classifier import TASK_CLASSIFIER_SYSTEM_PROMPT
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.integrations.chroma.store import VectorStoreProtocol
from app.integrations.job_search.openai_web_search import JobSearchProviderProtocol
from app.integrations.llm.shared import extract_json_object_text
from app.integrations.openai.client import (
    EmbeddingClientProtocol,
    LLMClientProtocol,
)
from app.modules.applications.repository import ApplicationRepository
from app.modules.applications.schemas import ApplicationCreateRequest, ApplicationUpdateRequest
from app.modules.applications.service import ApplicationService
from app.modules.approvals.schemas import ApprovalCreateRequest
from app.modules.approvals.service import ApprovalService
from app.modules.authentication.models import User
from app.modules.documents.generator import DocumentGeneratorProtocol
from app.modules.documents.schemas import CoverLetterRequest, TailorResumeRequest
from app.modules.documents.service import DocumentService
from app.modules.documents.validator import DocumentFactualityValidator
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.service import JobDiscoveryService
from app.modules.matching.service import JobMatchingService
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.rag.chunker import sanitize_untrusted_context
from app.modules.rag.service import RAGService
from app.modules.resume.models import ResumeFact
from app.repositories.audit_repository import AuditLogRepository


class AgentToolset:
    """Least-privilege domain tools exposed to LangGraph specialist nodes for one user."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        user: User,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None,
        vector_store: VectorStoreProtocol,
        job_search_provider: JobSearchProviderProtocol,
        document_generator: DocumentGeneratorProtocol,
    ) -> None:
        self._session = session
        self._settings = settings
        self._user = user
        self._llm = llm_client
        self._embeddings = embedding_client
        self._vectors = vector_store

        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._jobs_repo = JobRepository(session)
        self._apps_repo = ApplicationRepository(session)
        self._audit = AuditLogRepository(session)

        self._rag = RAGService(
            session=session,
            settings=settings,
            vector_store=vector_store,
            embedding_client=embedding_client,
        )
        self._job_discovery = JobDiscoveryService(
            session=session,
            settings=settings,
            search_provider=job_search_provider,
        )
        self._job_matching = JobMatchingService(
            session=session,
            embedding_client=embedding_client,
        )
        self._documents = DocumentService(
            session=session,
            generator=document_generator,
            validator=DocumentFactualityValidator(),
        )
        self._applications = ApplicationService(session)
        self._approvals = ApprovalService(session)

    @property
    def user(self) -> User:
        return self._user

    @property
    def max_tokens_budget(self) -> int:
        return max(self._settings.active_llm_max_tokens * 6, 12000)

    async def load_verified_profile(self) -> dict[str, Any]:
        """Load non-sensitive user-verified profile and skill identifiers."""
        profile = await self._profiles.get_by_user_id(self._user.id)
        skills = await self._skills.list_by_user_id(self._user.id)
        verified_fact_count = len(
            list(
                (
                    await self._session.scalars(
                        select(ResumeFact.id).where(
                            ResumeFact.user_id == self._user.id,
                            ResumeFact.is_verified.is_(True),
                        )
                    )
                ).all()
            )
        )
        return {
            "user_id": str(self._user.id),
            "full_name": self._user.full_name,
            "target_roles": list(profile.target_roles) if profile else [],
            "preferred_locations": list(profile.preferred_locations) if profile else [],
            "skill_count": len(skills),
            "verified_skill_names": [s.name for s in skills if s.is_verified][:25],
            "verified_fact_count": verified_fact_count,
        }

    async def classify_request(self, *, requested_task: str) -> tuple[str, str, int]:
        """Route user request via deterministic hints or LLM classifier JSON output."""
        lower = requested_task.lower()
        if any(kw in lower for kw in ("search job", "find job", "discover job", "openings")):
            return "job_discovery", "Matched job discovery intent.", 0
        if any(
            kw in lower
            for kw in ("prepare application", "tailor", "cover letter", "apply", "submit")
        ):
            return "application_prep", "Matched application preparation intent.", 0

        if not self._settings.ai_llm_configured:
            return "career_advisory", "Defaulted to career advisory (offline classifier).", 0

        safe_task = sanitize_untrusted_context(requested_task, max_chars=800)
        completion = await self._llm.complete_json(
            system_prompt=TASK_CLASSIFIER_SYSTEM_PROMPT,
            user_prompt=f"<user_request>\n{safe_task}\n</user_request>",
            max_tokens=200,
        )
        parsed = json.loads(extract_json_object_text(completion.content))
        category = str(parsed.get("task_category", "career_advisory"))
        if category not in {"job_discovery", "application_prep", "career_advisory"}:
            category = "career_advisory"
        reason = str(parsed.get("reason", "Classified by Workflow Router."))
        return category, reason, completion.total_tokens

    async def retrieve_rag_context(
        self, *, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Retrieve user-isolated context chunks from vector store."""
        hits = await self._rag.retrieve_context(
            user_id=self._user.id,
            query=query,
            top_k=top_k,
        )
        return [
            {
                "chunk_id": h.chunk_id,
                "score": h.score,
                "source_type": h.metadata.get("source_type"),
                "label": h.metadata.get("label"),
                "text": h.text,
            }
            for h in hits
        ]

    async def search_jobs(
        self,
        *,
        query: str,
        location: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Discover matching live or cached job listings."""
        response = await self._job_discovery.search_jobs(
            user=self._user,
            q=query,
            location=location,
            refresh=self._settings.ai_llm_configured,
            limit=limit,
        )
        return {
            "total": response.total,
            "source": response.source,
            "cached": response.cached,
            "jobs": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "company": item.company,
                    "location": item.location,
                    "external_url": item.external_url,
                }
                for item in response.items
            ],
        }

    async def match_job(self, *, job_id: str) -> dict[str, Any]:
        """Evaluate hybrid deterministic + semantic match score for target job."""
        parsed_id = uuid.UUID(job_id)
        match = await self._job_matching.calculate_match_for_job(
            user=self._user,
            job_id=parsed_id,
            use_semantic=self._settings.embeddings_configured,
        )
        return {
            "job_id": str(match.job_id),
            "overall_score": match.overall_score,
            "matching_skills": list(match.matching_skills),
            "missing_skills": list(match.missing_skills),
            "match_explanation": match.match_explanation,
            "recommended_preparation": list(match.recommended_preparation),
        }

    async def prepare_documents(
        self,
        *,
        job_id: str,
        resume_id: str | None = None,
        focus_instructions: str | None = None,
    ) -> dict[str, Any]:
        """Generate grounded tailored resume and cover letter for a target job."""
        job_uuid = uuid.UUID(job_id)
        resume_uuid = uuid.UUID(resume_id) if resume_id else None

        tailored = await self._documents.tailor_resume(
            user=self._user,
            payload=TailorResumeRequest(
                job_id=job_uuid,
                resume_id=resume_uuid,
                focus_instructions=focus_instructions,
            ),
        )
        cover_letter = await self._documents.generate_cover_letter(
            user=self._user,
            payload=CoverLetterRequest(
                job_id=job_uuid,
                resume_id=resume_uuid,
                custom_notes=focus_instructions,
            ),
        )
        tokens = int(tailored.tokens_used or 0) + int(cover_letter.tokens_used or 0)
        return {
            "tailored_resume": {
                "id": str(tailored.id),
                "title": tailored.title,
                "version": tailored.version,
                "is_grounded": bool(tailored.factuality_report.get("is_grounded", False)),
            },
            "cover_letter": {
                "id": str(cover_letter.id),
                "title": cover_letter.title,
                "version": cover_letter.version,
                "is_grounded": bool(cover_letter.factuality_report.get("is_grounded", False)),
            },
            "tokens_used": tokens,
        }

    async def prepare_submission_approval(
        self,
        *,
        workflow_id: str,
        job_id: str,
        application_id: str | None,
        documents_output: dict[str, Any],
        match_output: dict[str, Any] | None,
        requested_task: str,
    ) -> dict[str, Any]:
        """Link or create an Application and create a pending ApprovalRequest."""
        job_uuid = uuid.UUID(job_id)
        job = await self._jobs_repo.get_by_id(job_uuid)
        if job is None:
            raise NotFoundError("Target job listing not found.")

        resume_id_str = (documents_output.get("tailored_resume") or {}).get("id")
        cover_id_str = (documents_output.get("cover_letter") or {}).get("id")
        resume_uuid = uuid.UUID(resume_id_str) if resume_id_str else None
        cover_uuid = uuid.UUID(cover_id_str) if cover_id_str else None

        existing_app = None
        if application_id:
            existing_app = await self._apps_repo.get_by_id_for_user(
                application_id=uuid.UUID(application_id),
                user_id=self._user.id,
            )
        if existing_app is None:
            existing_app = await self._apps_repo.get_by_user_and_job(
                user_id=self._user.id,
                job_id=job_uuid,
            )

        if existing_app is None:
            app_detail = await self._applications.create_application(
                user_id=self._user.id,
                payload=ApplicationCreateRequest(
                    job_id=job_uuid,
                    tailored_resume_id=resume_uuid,
                    cover_letter_id=cover_uuid,
                    notes=f"Prepared by JobMate AI Agent Workflow {workflow_id}",
                ),
            )
            resolved_app_id = app_detail.id
        else:
            app_detail = await self._applications.update_application(
                user_id=self._user.id,
                application_id=existing_app.id,
                payload=ApplicationUpdateRequest(
                    tailored_resume_id=resume_uuid or existing_app.tailored_resume_id,
                    cover_letter_id=cover_uuid or existing_app.cover_letter_id,
                ),
            )
            resolved_app_id = app_detail.id

        approval_payload: dict[str, Any] = {
            "job_id": str(job.id),
            "company": job.company,
            "role": job.title,
            "tailored_resume": documents_output.get("tailored_resume"),
            "cover_letter": documents_output.get("cover_letter"),
            "match_score": match_output.get("overall_score") if match_output else None,
            "user_instruction": requested_task,
        }

        approval = await self._approvals.create_approval(
            user_id=self._user.id,
            workflow_run_id=uuid.UUID(workflow_id),
            payload=ApprovalCreateRequest(
                action_type="submit_application",
                application_id=resolved_app_id,
                target_destination=job.external_url,
                title=f"Submit Application: {job.title} at {job.company}",
                payload=approval_payload,
            ),
        )
        return {
            "approval_id": str(approval.id),
            "application_id": str(resolved_app_id),
            "status": approval.status,
            "target_destination": approval.target_destination,
            "title": approval.title,
        }

    async def generate_advisory(
        self,
        *,
        requested_task: str,
        profile_ref: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate structured RAG-grounded career advice using sanitized context."""
        context_block = "\n".join(
            f"- [{item.get('source_type')}: {item.get('label')}] "
            f"{sanitize_untrusted_context(str(item.get('text', '')), max_chars=500)}"
            for item in rag_context
        )
        safe_context = context_block or "No RAG chunks indexed yet."
        safe_question = sanitize_untrusted_context(requested_task, max_chars=800)
        prompt = (
            f"Candidate profile summary: {json.dumps(profile_ref)}\n\n"
            f"<untrusted_context>\n{safe_context}\n</untrusted_context>\n\n"
            f"User question: {safe_question}"
        )
        completion = await self._llm.complete_json(
            system_prompt=CAREER_ADVISORY_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=900,
        )
        parsed = json.loads(extract_json_object_text(completion.content))
        return {
            "summary": str(parsed.get("summary", "")),
            "strengths": list(parsed.get("strengths") or []),
            "recommended_actions": list(parsed.get("recommended_actions") or []),
            "cited_sources": list(parsed.get("cited_sources") or []),
            "tokens_used": completion.total_tokens,
        }

    async def record_workflow_audit(
        self,
        *,
        event_type: str,
        workflow_id: str,
        details: dict[str, Any],
    ) -> None:
        await self._audit.record(
            event_type=event_type,
            user_id=self._user.id,
            resource_type="workflow_run",
            resource_id=workflow_id,
            details=details,
        )
