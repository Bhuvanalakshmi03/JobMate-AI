"""Resume Intelligence domain service coordinating parsing, AI analysis, and verification."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.database.base import utc_now
from app.integrations.storage.local import StorageBackendProtocol
from app.modules.authentication.models import User
from app.modules.profile.models import UserSkill
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.resume.extractor import ResumeExtractorProtocol
from app.modules.resume.models import Resume, ResumeFact
from app.modules.resume.parser import ResumeParser
from app.modules.resume.repository import ResumeFactRepository, ResumeRepository
from app.modules.resume.schemas import (
    ResumeAnalysisResponse,
    ResumeDetailResponse,
    ResumeFactResponse,
    ResumeFactsPatchRequest,
    ResumeFactsPatchResponse,
    ResumeListResponse,
    ResumeSummaryResponse,
)
from app.modules.resume.validator import ResumeExtractionValidator
from app.repositories.audit_repository import AuditLogRepository

_VALID_SKILL_CATEGORIES = frozenset({"technical", "soft", "tool", "language", "framework"})
_VALID_PROFICIENCIES = frozenset({"beginner", "intermediate", "advanced", "expert"})


def _safe_http_url_or_none(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return trimmed[:512]
    return None


class ResumeService:
    """Orchestrates resume storage, extraction, fact verification, and profile sync."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        storage: StorageBackendProtocol,
        parser: ResumeParser,
        extractor: ResumeExtractorProtocol,
        validator: ResumeExtractionValidator,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage
        self._parser = parser
        self._extractor = extractor
        self._validator = validator
        self._resumes = ResumeRepository(session)
        self._facts = ResumeFactRepository(session)
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._audit = AuditLogRepository(session)

    async def _require_owned_resume(self, *, user: User, resume_id: uuid.UUID) -> Resume:
        resume = await self._resumes.get_by_id_for_user(resume_id=resume_id, user_id=user.id)
        if resume is None:
            raise NotFoundError("Resume not found.")
        return resume

    async def upload_resume(
        self,
        *,
        user: User,
        filename: str | None,
        content_type: str | None,
        data: bytes,
    ) -> ResumeSummaryResponse:
        """Validate, store privately, and extract text from a PDF or DOCX resume."""
        validated = self._parser.validate(
            filename=filename,
            content_type=content_type,
            data=data,
        )
        parsed = self._parser.parse(extension=validated.extension, data=data)

        resume_id = uuid.uuid4()
        storage_key = f"resumes/{user.id}/{resume_id}.{validated.extension}"
        await self._storage.save_bytes(key=storage_key, data=data)

        try:
            resume = await self._resumes.create(
                resume_id=resume_id,
                user_id=user.id,
                original_filename=validated.safe_filename,
                storage_key=storage_key,
                content_type=validated.content_type,
                file_extension=validated.extension,
                file_size_bytes=validated.size_bytes,
                sha256_hash=validated.sha256_hash,
                page_count=parsed.page_count,
                extracted_text=parsed.text,
                parse_status="parsed",
            )
            await self._audit.record(
                event_type="resume.uploaded",
                user_id=user.id,
                resource_type="resume",
                resource_id=str(resume_id),
                details={
                    "extension": validated.extension,
                    "size_bytes": validated.size_bytes,
                    "page_count": parsed.page_count,
                },
            )
        except Exception:
            await self._storage.delete(key=storage_key)
            raise

        return ResumeSummaryResponse.model_validate(resume)

    async def list_resumes(
        self,
        *,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> ResumeListResponse:
        rows, total = await self._resumes.list_by_user(
            user_id=user.id,
            limit=limit,
            offset=offset,
        )
        return ResumeListResponse(
            items=[ResumeSummaryResponse.model_validate(row) for row in rows],
            total=total,
        )

    async def get_resume(self, *, user: User, resume_id: uuid.UUID) -> ResumeDetailResponse:
        resume = await self._require_owned_resume(user=user, resume_id=resume_id)
        fact_count, verified_count = await self._facts.count_stats(
            resume_id=resume.id,
            user_id=user.id,
        )
        base = ResumeSummaryResponse.model_validate(resume)
        return ResumeDetailResponse(
            **base.model_dump(),
            extracted_text=resume.extracted_text,
            analysis_summary=resume.analysis_summary,
            fact_count=fact_count,
            verified_fact_count=verified_count,
        )

    async def analyze_resume(
        self,
        *,
        user: User,
        resume_id: uuid.UUID,
        force: bool = False,
    ) -> ResumeAnalysisResponse:
        """Run AI resume intelligence extraction unless an unchanged analysis is cached."""
        resume = await self._require_owned_resume(user=user, resume_id=resume_id)

        if (
            not force
            and resume.parse_status == "analyzed"
            and resume.analysis_summary is not None
        ):
            existing_facts = await self._facts.list_for_resume(
                resume_id=resume.id,
                user_id=user.id,
            )
            return self._build_analysis_response(resume=resume, facts=existing_facts)

        if not resume.extracted_text or not resume.extracted_text.strip():
            raise ValidationError("Resume does not contain extracted text for analysis.")

        try:
            raw_output = await self._extractor.extract(resume_text=resume.extracted_text)
            validated = self._validator.validate(
                raw_json=raw_output.raw_json,
                source_text=resume.extracted_text,
            )
        except Exception as exc:
            resume.parse_status = "failed"
            resume.error_message = str(exc)[:500]
            await self._session.flush()
            raise

        summary_payload: dict[str, Any] = {
            "overall_assessment": validated.overall_assessment,
            "strengths": validated.strengths,
            "weaknesses": validated.weaknesses,
            "missing_skills": validated.missing_skills,
            "recommendations": validated.recommendations,
            "model_used": raw_output.model,
            "tokens_used": raw_output.total_tokens,
        }

        fact_records_data = [
            {
                "fact_type": item.fact_type,
                "title": item.title,
                "organization": item.organization,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "description": item.description,
                "structured_data": item.structured_data,
                "source_section": item.source_section,
                "evidence_excerpt": item.evidence_excerpt,
                "confidence": item.confidence,
                "verification_status": "pending",
                "is_verified": False,
                "verified_at": None,
            }
            for item in validated.facts
        ]

        stored_facts = await self._facts.replace_unverified_extracted_facts(
            resume_id=resume.id,
            user_id=user.id,
            facts=fact_records_data,
        )

        resume.completeness_score = round(validated.completeness_score, 1)
        resume.analysis_summary = summary_payload
        resume.parse_status = "analyzed"
        resume.error_message = None
        resume.analyzed_at = utc_now()
        await self._session.flush()

        await self._audit.record(
            event_type="resume.analyzed",
            user_id=user.id,
            resource_type="resume",
            resource_id=str(resume.id),
            details={
                "model": raw_output.model,
                "tokens_used": raw_output.total_tokens,
                "fact_count": len(stored_facts),
            },
        )
        return self._build_analysis_response(resume=resume, facts=stored_facts)

    async def get_analysis(
        self,
        *,
        user: User,
        resume_id: uuid.UUID,
    ) -> ResumeAnalysisResponse:
        resume = await self._require_owned_resume(user=user, resume_id=resume_id)
        facts = await self._facts.list_for_resume(resume_id=resume.id, user_id=user.id)
        return self._build_analysis_response(resume=resume, facts=facts)

    async def patch_facts(
        self,
        *,
        user: User,
        resume_id: uuid.UUID,
        payload: ResumeFactsPatchRequest,
    ) -> ResumeFactsPatchResponse:
        """Verify, correct, or reject extracted facts and sync verified facts to profile."""
        resume = await self._require_owned_resume(user=user, resume_id=resume_id)
        existing_facts = await self._facts.list_for_resume(resume_id=resume.id, user_id=user.id)
        facts_by_id = {fact.id: fact for fact in existing_facts}

        for update_item in payload.updates:
            if update_item.fact_id not in facts_by_id:
                raise NotFoundError(f"Resume fact {update_item.fact_id} not found.")

        now = utc_now()
        for update_item in payload.updates:
            fact = facts_by_id[update_item.fact_id]
            if update_item.action == "reject":
                fact.verification_status = "rejected"
                fact.is_verified = False
                fact.verified_at = None
                continue

            if update_item.action == "edit":
                if update_item.title is not None:
                    fact.title = update_item.title.strip()
                if update_item.organization is not None:
                    fact.organization = update_item.organization.strip() or None
                if update_item.start_date is not None:
                    fact.start_date = update_item.start_date.strip() or None
                if update_item.end_date is not None:
                    fact.end_date = update_item.end_date.strip() or None
                if update_item.description is not None:
                    fact.description = update_item.description.strip() or None
                if update_item.structured_data is not None:
                    fact.structured_data = update_item.structured_data
                fact.verification_status = "edited"
            else:
                fact.verification_status = "verified"

            fact.is_verified = True
            fact.verified_at = now

        await self._session.flush()

        synced_skills_count = 0
        if payload.sync_to_profile:
            synced_skills_count = await self._sync_verified_facts_to_profile(
                user=user,
                facts=existing_facts,
            )

        verified_count = sum(1 for f in existing_facts if f.is_verified)
        await self._audit.record(
            event_type="resume.facts_verified",
            user_id=user.id,
            resource_type="resume",
            resource_id=str(resume.id),
            details={
                "updated_count": len(payload.updates),
                "verified_count": verified_count,
                "synced_to_profile": payload.sync_to_profile,
                "synced_skills_count": synced_skills_count,
            },
        )
        return ResumeFactsPatchResponse(
            facts=[ResumeFactResponse.model_validate(f) for f in existing_facts],
            verified_count=verified_count,
            synced_to_profile=payload.sync_to_profile,
            synced_skills_count=synced_skills_count,
        )

    async def delete_resume(self, *, user: User, resume_id: uuid.UUID) -> None:
        """Delete resume metadata, extracted facts, and stored original artifact."""
        resume = await self._require_owned_resume(user=user, resume_id=resume_id)
        storage_key = resume.storage_key
        await self._resumes.delete_record(resume)
        await self._storage.delete(key=storage_key)
        await self._audit.record(
            event_type="resume.deleted",
            user_id=user.id,
            resource_type="resume",
            resource_id=str(resume_id),
        )

    async def _sync_verified_facts_to_profile(
        self,
        *,
        user: User,
        facts: list[ResumeFact],
    ) -> int:
        verified_facts = [f for f in facts if f.is_verified and f.verification_status != "rejected"]
        if not verified_facts:
            return 0

        profile = await self._profiles.get_by_user_id(user.id)
        profile_updates: dict[str, Any] = {"profile_verified": True}

        for fact in verified_facts:
            data = fact.structured_data or {}
            if fact.fact_type == "personal_info":
                if isinstance(data.get("location"), str) and data["location"].strip():
                    profile_updates["location"] = data["location"].strip()[:255]
                if isinstance(data.get("phone"), str) and data["phone"].strip():
                    profile_updates["phone"] = data["phone"].strip()[:50]
                if isinstance(data.get("headline"), str) and data["headline"].strip():
                    profile_updates["headline"] = data["headline"].strip()[:255]
                for url_field in ("linkedin_url", "github_url", "portfolio_url"):
                    safe_url = _safe_http_url_or_none(data.get(url_field))
                    if safe_url:
                        profile_updates[url_field] = safe_url
            elif fact.fact_type == "education":
                if fact.organization and fact.organization.strip():
                    profile_updates["university"] = fact.organization.strip()[:255]
                elif isinstance(data.get("university"), str) and data["university"].strip():
                    profile_updates["university"] = data["university"].strip()[:255]
                degree_val = data.get("degree") or fact.title
                if isinstance(degree_val, str) and degree_val.strip():
                    profile_updates["degree"] = degree_val.strip()[:255]
                grad_year = data.get("graduation_year")
                if isinstance(grad_year, int) and 1970 <= grad_year <= 2050:
                    profile_updates["graduation_year"] = grad_year

        if profile is None:
            await self._profiles.create(
                user_id=user.id,
                fields={
                    "target_roles": [],
                    "preferred_locations": [],
                    "work_mode_preferences": [],
                    "ai_consent_given": False,
                    "notification_consent": False,
                    **profile_updates,
                },
            )
        else:
            await self._profiles.update(profile, fields=profile_updates)

        skill_facts = [f for f in verified_facts if f.fact_type == "skill"]
        if not skill_facts:
            return 0

        existing_skills = list(
            (
                await self._session.scalars(
                    select(UserSkill).where(UserSkill.user_id == user.id)
                )
            ).all()
        )
        existing_map = {
            (s.normalized_name, s.category): s for s in existing_skills
        }
        synced_count = 0
        for fact in skill_facts:
            name = fact.title.strip()[:120]
            normalized = name.lower()
            data = fact.structured_data or {}
            raw_cat = str(data.get("category", "technical")).lower()
            category = raw_cat if raw_cat in _VALID_SKILL_CATEGORIES else "technical"
            raw_prof = str(data.get("proficiency", "intermediate")).lower()
            proficiency = raw_prof if raw_prof in _VALID_PROFICIENCIES else "intermediate"

            key = (normalized, category)
            if key in existing_map:
                existing = existing_map[key]
                existing.is_verified = True
                if existing.source != "manual":
                    existing.source = "resume_verified"
                    existing.proficiency = proficiency
            else:
                new_skill = UserSkill(
                    user_id=user.id,
                    name=name,
                    normalized_name=normalized,
                    category=category,
                    proficiency=proficiency,
                    is_verified=True,
                    source="resume_verified",
                )
                self._session.add(new_skill)
                existing_map[key] = new_skill
            synced_count += 1

        await self._session.flush()
        return synced_count

    def _build_analysis_response(
        self,
        *,
        resume: Resume,
        facts: list[ResumeFact],
    ) -> ResumeAnalysisResponse:
        return ResumeAnalysisResponse(
            resume=ResumeSummaryResponse.model_validate(resume),
            completeness_score=resume.completeness_score,
            analysis_summary=resume.analysis_summary,
            facts=[ResumeFactResponse.model_validate(fact) for fact in facts],
        )
