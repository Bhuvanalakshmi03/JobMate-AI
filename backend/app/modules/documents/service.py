"""Document generation service orchestrating verified facts, validation, versioning, and export."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.authentication.models import User
from app.modules.documents.exporter import (
    export_document_bytes,
    render_application_note_markdown,
    render_cover_letter_markdown,
    render_tailored_resume_markdown,
)
from app.modules.documents.generator import (
    DocumentGeneratorProtocol,
    JobTargetContext,
    VerifiedCandidateContext,
)
from app.modules.documents.models import GeneratedDocument
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import (
    ApplicationNoteRequest,
    CoverLetterRequest,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionSummary,
    ExportFormat,
    TailorResumeRequest,
)
from app.modules.documents.validator import DocumentFactualityValidator
from app.modules.jobs.repository import JobRepository
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.resume.models import ResumeFact
from app.modules.resume.repository import ResumeRepository
from app.repositories.audit_repository import AuditLogRepository


class DocumentService:
    """Generates, validates, versions, edits, and exports job-specific career documents."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        generator: DocumentGeneratorProtocol,
        validator: DocumentFactualityValidator,
    ) -> None:
        self._session = session
        self._generator = generator
        self._validator = validator
        self._docs = DocumentRepository(session)
        self._jobs = JobRepository(session)
        self._resumes = ResumeRepository(session)
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._audit = AuditLogRepository(session)

    async def _load_verified_candidate_context(
        self,
        *,
        user: User,
        resume_id: uuid.UUID | None,
    ) -> VerifiedCandidateContext:
        if resume_id is not None:
            resume = await self._resumes.get_by_id_for_user(resume_id=resume_id, user_id=user.id)
            if resume is None:
                raise NotFoundError("Source resume not found.")

        profile = await self._profiles.get_by_user_id(user.id)
        skills = await self._skills.list_by_user_id(user.id)
        verified_skills = [s.name for s in skills if s.is_verified]

        stmt = select(ResumeFact).where(
            ResumeFact.user_id == user.id,
            ResumeFact.is_verified.is_(True),
            ResumeFact.verification_status != "rejected",
        )
        if resume_id is not None:
            stmt = stmt.where(ResumeFact.resume_id == resume_id)

        facts = list(
            (await self._session.scalars(stmt.order_by(ResumeFact.created_at.asc()))).all()
        )

        has_profile_substance = bool(
            profile
            and (profile.headline or profile.summary or profile.university or profile.degree)
        )
        if not facts and not verified_skills and not has_profile_substance:
            raise ValidationError(
                "Verify at least one resume fact or save your career profile and skills "
                "before generating tailored documents."
            )

        serialized_facts = [
            {
                "id": str(f.id),
                "fact_type": f.fact_type,
                "title": f.title,
                "organization": f.organization,
                "start_date": f.start_date,
                "end_date": f.end_date,
                "description": f.description,
                "structured_data": f.structured_data,
            }
            for f in facts
        ]

        return VerifiedCandidateContext(
            full_name=user.full_name,
            email=user.email,
            location=profile.location if profile else None,
            headline=profile.headline if profile else None,
            summary=profile.summary if profile else None,
            university=profile.university if profile else None,
            degree=profile.degree if profile else None,
            graduation_year=profile.graduation_year if profile else None,
            linkedin_url=profile.linkedin_url if profile else None,
            github_url=profile.github_url if profile else None,
            portfolio_url=profile.portfolio_url if profile else None,
            verified_skills=verified_skills,
            verified_facts=serialized_facts,
            verified_fact_ids=[str(f.id) for f in facts],
        )

    async def _load_job_context(self, job_id: uuid.UUID) -> JobTargetContext:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Target job listing not found.")
        return JobTargetContext(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            required_skills=list(job.required_skills),
            preferred_skills=list(job.preferred_skills),
        )

    async def tailor_resume(
        self,
        *,
        user: User,
        payload: TailorResumeRequest,
    ) -> DocumentResponse:
        candidate = await self._load_verified_candidate_context(
            user=user,
            resume_id=payload.resume_id,
        )
        job = await self._load_job_context(payload.job_id)
        draft = await self._generator.generate_tailored_resume(
            candidate=candidate,
            job=job,
            focus_instructions=payload.focus_instructions,
        )
        structured, factuality = self._validator.validate_tailored_resume(
            raw_json=draft.raw_json,
            candidate=candidate,
            job=job,
        )
        markdown = render_tailored_resume_markdown(candidate=candidate, structured=structured)
        doc = await self._docs.create(
            user_id=user.id,
            job_id=payload.job_id,
            source_resume_id=payload.resume_id,
            document_type="tailored_resume",
            title=f"{job.title} at {job.company} — Tailored Resume",
            version_group_id=uuid.uuid4(),
            version=1,
            content_markdown=markdown,
            structured_content=structured.model_dump(),
            factuality_report=factuality.to_dict(),
            is_user_edited=False,
            model_used=draft.model,
            tokens_used=draft.total_tokens,
        )
        await self._audit.record(
            event_type="documents.tailored_resume_generated",
            user_id=user.id,
            resource_type="generated_document",
            resource_id=str(doc.id),
            details={"job_id": str(payload.job_id), "tokens": draft.total_tokens},
        )
        return DocumentResponse.model_validate(doc)

    async def generate_cover_letter(
        self,
        *,
        user: User,
        payload: CoverLetterRequest,
    ) -> DocumentResponse:
        candidate = await self._load_verified_candidate_context(
            user=user,
            resume_id=payload.resume_id,
        )
        job = await self._load_job_context(payload.job_id)
        draft = await self._generator.generate_cover_letter(
            candidate=candidate,
            job=job,
            tone=payload.tone,
            custom_notes=payload.custom_notes,
        )
        structured, factuality = self._validator.validate_cover_letter(
            raw_json=draft.raw_json,
            candidate=candidate,
            job=job,
        )
        markdown = render_cover_letter_markdown(candidate=candidate, structured=structured)
        doc = await self._docs.create(
            user_id=user.id,
            job_id=payload.job_id,
            source_resume_id=payload.resume_id,
            document_type="cover_letter",
            title=f"{job.title} at {job.company} — Cover Letter",
            version_group_id=uuid.uuid4(),
            version=1,
            content_markdown=markdown,
            structured_content=structured.model_dump(),
            factuality_report=factuality.to_dict(),
            is_user_edited=False,
            model_used=draft.model,
            tokens_used=draft.total_tokens,
        )
        await self._audit.record(
            event_type="documents.cover_letter_generated",
            user_id=user.id,
            resource_type="generated_document",
            resource_id=str(doc.id),
            details={"job_id": str(payload.job_id), "tokens": draft.total_tokens},
        )
        return DocumentResponse.model_validate(doc)

    async def generate_application_note(
        self,
        *,
        user: User,
        payload: ApplicationNoteRequest,
    ) -> DocumentResponse:
        candidate = await self._load_verified_candidate_context(
            user=user,
            resume_id=payload.resume_id,
        )
        job = await self._load_job_context(payload.job_id)
        draft = await self._generator.generate_application_note(
            candidate=candidate,
            job=job,
            max_words=payload.max_words,
        )
        structured, factuality = self._validator.validate_application_note(
            raw_json=draft.raw_json,
            candidate=candidate,
            job=job,
        )
        markdown = render_application_note_markdown(structured)
        doc = await self._docs.create(
            user_id=user.id,
            job_id=payload.job_id,
            source_resume_id=payload.resume_id,
            document_type="application_note",
            title=f"{job.title} at {job.company} — Application Note",
            version_group_id=uuid.uuid4(),
            version=1,
            content_markdown=markdown,
            structured_content=structured.model_dump(),
            factuality_report=factuality.to_dict(),
            is_user_edited=False,
            model_used=draft.model,
            tokens_used=draft.total_tokens,
        )
        await self._audit.record(
            event_type="documents.application_note_generated",
            user_id=user.id,
            resource_type="generated_document",
            resource_id=str(doc.id),
            details={"job_id": str(payload.job_id), "tokens": draft.total_tokens},
        )
        return DocumentResponse.model_validate(doc)

    async def _require_owned_document(
        self,
        *,
        user: User,
        document_id: uuid.UUID,
    ) -> GeneratedDocument:
        doc = await self._docs.get_by_id_for_user(document_id=document_id, user_id=user.id)
        if doc is None:
            raise NotFoundError("Generated document not found.")
        return doc

    async def list_documents(
        self,
        *,
        user: User,
        job_id: uuid.UUID | None = None,
        document_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DocumentListResponse:
        rows, total = await self._docs.list_for_user(
            user_id=user.id,
            job_id=job_id,
            document_type=document_type,
            limit=limit,
            offset=offset,
        )
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(r) for r in rows],
            total=total,
        )

    async def get_document(
        self,
        *,
        user: User,
        document_id: uuid.UUID,
    ) -> DocumentDetailResponse:
        doc = await self._require_owned_document(user=user, document_id=document_id)
        versions = await self._docs.list_versions(
            version_group_id=doc.version_group_id,
            user_id=user.id,
        )
        base = DocumentResponse.model_validate(doc)
        return DocumentDetailResponse(
            **base.model_dump(),
            versions=[DocumentVersionSummary.model_validate(v) for v in versions],
        )

    async def update_document(
        self,
        *,
        user: User,
        document_id: uuid.UUID,
        payload: DocumentUpdateRequest,
    ) -> DocumentDetailResponse:
        doc = await self._require_owned_document(user=user, document_id=document_id)
        new_title = payload.title.strip() if payload.title else doc.title
        new_markdown = (
            payload.content_markdown.strip()
            if payload.content_markdown is not None
            else doc.content_markdown
        )
        new_structured = (
            payload.structured_content
            if payload.structured_content is not None
            else doc.structured_content
        )

        if payload.create_new_version:
            latest_ver = await self._docs.get_latest_version_number(
                version_group_id=doc.version_group_id,
                user_id=user.id,
            )
            saved_doc = await self._docs.create(
                user_id=user.id,
                job_id=doc.job_id,
                source_resume_id=doc.source_resume_id,
                document_type=doc.document_type,
                title=new_title,
                version_group_id=doc.version_group_id,
                version=latest_ver + 1,
                content_markdown=new_markdown,
                structured_content=new_structured,
                factuality_report=dict(doc.factuality_report),
                is_user_edited=True,
                model_used=doc.model_used,
                tokens_used=0,
            )
        else:
            doc.title = new_title
            doc.content_markdown = new_markdown
            doc.structured_content = new_structured
            doc.is_user_edited = True
            await self._session.flush()
            saved_doc = doc

        await self._audit.record(
            event_type="documents.edited",
            user_id=user.id,
            resource_type="generated_document",
            resource_id=str(saved_doc.id),
            details={"version": saved_doc.version, "new_version": payload.create_new_version},
        )
        return await self.get_document(user=user, document_id=saved_doc.id)

    async def export_document(
        self,
        *,
        user: User,
        document_id: uuid.UUID,
        export_format: ExportFormat,
    ) -> tuple[bytes, str, str]:
        doc = await self._require_owned_document(user=user, document_id=document_id)
        data, media_type, filename = export_document_bytes(
            title=doc.title,
            content_markdown=doc.content_markdown,
            export_format=export_format,
        )
        await self._audit.record(
            event_type="documents.exported",
            user_id=user.id,
            resource_type="generated_document",
            resource_id=str(doc.id),
            details={"format": export_format},
        )
        return data, media_type, filename
