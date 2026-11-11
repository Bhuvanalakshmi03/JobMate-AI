"""OpenAI function-calling tool schemas and user-scoped executors for Co-Pilot Chat."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.chroma.store import VectorStoreProtocol
from app.integrations.job_search.openai_web_search import JobSearchProviderProtocol
from app.integrations.openai.client import EmbeddingClientProtocol
from app.modules.applications.repository import ApplicationRepository
from app.modules.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationTransitionRequest,
    ApplicationUpdateRequest,
)
from app.modules.applications.service import ApplicationService
from app.modules.approvals.schemas import ApprovalCreateRequest
from app.modules.approvals.service import ApprovalService
from app.modules.authentication.models import User
from app.modules.calendar.service import CalendarService
from app.modules.documents.generator import DocumentGeneratorProtocol
from app.modules.documents.schemas import (
    ApplicationNoteRequest,
    CoverLetterRequest,
    TailorResumeRequest,
)
from app.modules.documents.service import DocumentService
from app.modules.documents.validator import DocumentFactualityValidator
from app.modules.interviews.service import InterviewService
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.service import JobDiscoveryService
from app.modules.matching.service import JobMatchingService
from app.modules.memory.schemas import CareerMemoryCreateRequest
from app.modules.memory.service import CareerMemoryService
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.profile.schemas import ProfileUpdateRequest
from app.modules.profile.service import ProfileService
from app.modules.rag.service import RAGService
from app.modules.reminders.schemas import ReminderCreateRequest
from app.modules.reminders.service import ReminderService
from app.modules.resume.repository import ResumeRepository


def _parse_uuid(raw: object, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(raw).strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid UUID provided for {label}.") from exc


def _parse_optional_dt(raw: object) -> datetime | None:
    if raw is None or not str(raw).strip():
        return None
    cleaned = str(raw).strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    return datetime.fromisoformat(cleaned)


def _tool_def(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


COPILOT_TOOL_SCHEMAS: list[dict[str, Any]] = [
    _tool_def(
        "get_profile_and_skills",
        "Fetch the student's verified profile, target roles, locations, skills, and resumes.",
        {},
    ),
    _tool_def(
        "update_career_profile",
        "Update headline, summary, location, target_roles, or preferred_locations cleanly.",
        {
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            "location": {"type": "string"},
            "target_roles": {"type": "array", "items": {"type": "string"}},
            "preferred_locations": {"type": "array", "items": {"type": "string"}},
        },
    ),
    _tool_def(
        "search_jobs",
        "Search live web jobs (OpenAI Web Search) or stored job listings with filters.",
        {
            "query": {"type": "string"},
            "location": {"type": "string"},
            "work_mode": {"type": "string", "enum": ["remote", "hybrid", "onsite"]},
            "experience_level": {
                "type": "string",
                "enum": ["student", "intern", "entry_level", "junior", "mid_level", "senior"],
            },
            "refresh": {"type": "boolean"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        required=["query"],
    ),
    _tool_def(
        "calculate_job_match",
        "Compute deterministic + semantic match score and skill gaps for a specific job_id.",
        {"job_id": {"type": "string"}},
        required=["job_id"],
    ),
    _tool_def(
        "generate_tailored_document",
        "Generate a fact-grounded tailored_resume, cover_letter, or application_note for a job.",
        {
            "job_id": {"type": "string"},
            "document_type": {
                "type": "string",
                "enum": ["tailored_resume", "cover_letter", "application_note"],
            },
            "resume_id": {"type": "string"},
            "focus_instructions": {"type": "string"},
        },
        required=["job_id", "document_type"],
    ),
    _tool_def(
        "list_applications",
        "List the student's tracked applications, pipeline summary counts, and deadlines.",
        {
            "status": {
                "type": "string",
                "enum": [
                    "SAVED",
                    "PREPARING",
                    "AWAITING_APPROVAL",
                    "SUBMITTED",
                    "INTERVIEW_SCHEDULED",
                    "REJECTED",
                    "OFFER_RECEIVED",
                    "WITHDRAWN",
                ],
            },
        },
    ),
    _tool_def(
        "create_or_update_application",
        "Create a tracked job application, update notes/deadlines, or run a safe status transition "
        "(SUBMITTED requires prepare_application_submission for human confirmation).",
        {
            "application_id": {"type": "string"},
            "job_id": {"type": "string"},
            "company_name": {"type": "string"},
            "role_title": {"type": "string"},
            "job_url": {"type": "string"},
            "location": {"type": "string"},
            "deadline_at": {"type": "string", "description": "ISO-8601 datetime"},
            "follow_up_at": {"type": "string", "description": "ISO-8601 datetime"},
            "notes": {"type": "string"},
            "transition_to": {
                "type": "string",
                "enum": [
                    "SAVED",
                    "PREPARING",
                    "INTERVIEW_SCHEDULED",
                    "OFFER_RECEIVED",
                    "REJECTED",
                    "WITHDRAWN",
                ],
            },
            "transition_note": {"type": "string"},
        },
    ),
    _tool_def(
        "prepare_application_submission",
        "Prepare a human-approval request to submit a job application "
        "(moves app to AWAITING_APPROVAL).",
        {
            "application_id": {"type": "string"},
            "job_id": {"type": "string"},
            "notes": {"type": "string"},
        },
    ),
    _tool_def(
        "list_pending_approvals",
        "Inspect pending or historical human approval requests awaiting confirmation.",
        {"status": {"type": "string"}},
    ),
    _tool_def(
        "sync_career_knowledge",
        "Index the student's verified profile, resume facts, and documents into ChromaDB RAG.",
        {},
    ),
    _tool_def(
        "query_career_knowledge",
        "Retrieve semantic career context from ChromaDB scoped strictly to the user.",
        {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        required=["query"],
    ),
    _tool_def(
        "list_calendar_events",
        "Fetch upcoming events from the student's connected Google Calendar (defaults to 7 days).",
        {
            "days_ahead": {"type": "integer", "minimum": 1, "maximum": 90},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
        },
    ),
    _tool_def(
        "propose_calendar_event",
        "Prepare a Google Calendar event approval request "
        "(interview prep, interview slot, or follow-up) requiring user confirmation.",
        {
            "summary": {"type": "string"},
            "start_iso": {"type": "string", "description": "ISO-8601 start timestamp with offset"},
            "end_iso": {"type": "string", "description": "ISO-8601 end timestamp with offset"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "timezone": {"type": "string"},
        },
        required=["summary", "start_iso", "end_iso"],
    ),
    _tool_def(
        "list_interview_sessions",
        "List the student's mock interview preparation sessions and scores.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
    ),
    _tool_def(
        "get_skill_gap_plan",
        "Analyze skill gaps across job matches and mock interview feedback.",
        {},
    ),
    _tool_def(
        "list_career_memory",
        "List user-approved Career Memory preferences, goals, and notes.",
        {"approved_only": {"type": "boolean"}},
    ),
    _tool_def(
        "save_career_memory",
        "Save a persistent Career Memory note or preference when user consent is enabled.",
        {
            "category": {
                "type": "string",
                "enum": ["preference", "goal", "strength", "weakness", "note"],
            },
            "title": {"type": "string"},
            "content": {"type": "string"},
            "memory_key": {"type": "string"},
        },
        required=["title", "content"],
    ),
    _tool_def(
        "list_reminders",
        "List scheduled reminders and due in-app notifications.",
        {"status": {"type": "string"}},
    ),
    _tool_def(
        "schedule_reminder",
        "Schedule a timezone-aware deduplicated reminder for a deadline or follow-up.",
        {
            "title": {"type": "string"},
            "message": {"type": "string"},
            "scheduled_for": {"type": "string", "description": "ISO-8601 timestamp"},
            "reminder_type": {
                "type": "string",
                "enum": ["deadline", "follow_up", "interview", "study_plan", "custom"],
            },
            "dedup_key": {"type": "string"},
            "timezone": {"type": "string"},
        },
        required=["title", "scheduled_for"],
    ),
]


class CopilotChatToolkit:
    """Executes user-isolated JobMate AI and Google Calendar tool calls from Co-Pilot Chat."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        user: User,
        embedding_client: EmbeddingClientProtocol,
        vector_store: VectorStoreProtocol,
        job_search_provider: JobSearchProviderProtocol,
        document_generator: DocumentGeneratorProtocol,
        calendar_service: CalendarService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._user = user
        self._calendar = calendar_service

        self._profiles_repo = ProfileRepository(session)
        self._skills_repo = SkillRepository(session)
        self._resumes_repo = ResumeRepository(session)
        self._jobs_repo = JobRepository(session)
        self._apps_repo = ApplicationRepository(session)

        self._profile_service = ProfileService(session)
        self._job_discovery = JobDiscoveryService(
            session=session,
            settings=settings,
            search_provider=job_search_provider,
        )
        self._job_matching = JobMatchingService(session=session, embedding_client=embedding_client)
        self._documents = DocumentService(
            session=session,
            generator=document_generator,
            validator=DocumentFactualityValidator(),
        )
        self._applications = ApplicationService(session)
        self._approvals = ApprovalService(
            session=session,
            settings=settings,
            calendar_service=calendar_service,
        )
        self._rag = RAGService(
            session=session,
            settings=settings,
            vector_store=vector_store,
            embedding_client=embedding_client,
        )
        self._interviews = InterviewService(session=session, settings=settings)
        self._memory = CareerMemoryService(session)
        self._reminders = ReminderService(session=session)
        self.created_approval_ids: list[str] = []

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        handlers = {
            "get_profile_and_skills": self._get_profile_and_skills,
            "update_career_profile": self._update_career_profile,
            "search_jobs": self._search_jobs,
            "calculate_job_match": self._calculate_job_match,
            "generate_tailored_document": self._generate_tailored_document,
            "list_applications": self._list_applications,
            "create_or_update_application": self._create_or_update_application,
            "prepare_application_submission": self._prepare_application_submission,
            "list_pending_approvals": self._list_pending_approvals,
            "sync_career_knowledge": self._sync_career_knowledge,
            "query_career_knowledge": self._query_career_knowledge,
            "list_calendar_events": self._list_calendar_events,
            "propose_calendar_event": self._propose_calendar_event,
            "list_interview_sessions": self._list_interview_sessions,
            "get_skill_gap_plan": self._get_skill_gap_plan,
            "list_career_memory": self._list_career_memory,
            "save_career_memory": self._save_career_memory,
            "list_reminders": self._list_reminders,
            "schedule_reminder": self._schedule_reminder,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool '{tool_name}'."})
        result = await handler(arguments)
        return json.dumps(result, default=str)

    async def _get_profile_and_skills(self, _args: dict[str, Any]) -> dict[str, Any]:
        profile = await self._profiles_repo.get_by_user_id(self._user.id)
        skills = await self._skills_repo.list_by_user_id(self._user.id)
        resumes, _ = await self._resumes_repo.list_by_user(user_id=self._user.id, limit=10)
        return {
            "user": {
                "full_name": self._user.full_name,
                "email": self._user.email,
                "timezone": self._user.timezone,
            },
            "profile": {
                "headline": profile.headline,
                "summary": profile.summary,
                "location": profile.location,
                "university": profile.university,
                "degree": profile.degree,
                "experience_level": profile.experience_level,
                "target_roles": list(profile.target_roles),
                "preferred_locations": list(profile.preferred_locations),
            }
            if profile
            else None,
            "skills": [
                {"name": s.name, "category": s.category, "is_verified": s.is_verified}
                for s in skills
            ],
            "resumes": [
                {
                    "id": str(r.id),
                    "filename": r.original_filename,
                    "parse_status": r.parse_status,
                    "completeness_score": r.completeness_score,
                }
                for r in resumes
            ],
        }

    async def _update_career_profile(self, args: dict[str, Any]) -> dict[str, Any]:
        existing = await self._profiles_repo.get_by_user_id(self._user.id)
        payload = ProfileUpdateRequest(
            headline=args.get("headline", existing.headline if existing else None),
            summary=args.get("summary", existing.summary if existing else None),
            location=args.get("location", existing.location if existing else None),
            university=existing.university if existing else None,
            degree=existing.degree if existing else None,
            graduation_year=existing.graduation_year if existing else None,
            experience_level=existing.experience_level if existing else None,
            years_of_experience=existing.years_of_experience if existing else None,
            target_roles=args.get(
                "target_roles", list(existing.target_roles) if existing else []
            ),
            preferred_locations=args.get(
                "preferred_locations", list(existing.preferred_locations) if existing else []
            ),
            work_mode_preferences=(
                list(existing.work_mode_preferences) if existing else []
            ),
            linkedin_url=existing.linkedin_url if existing else None,
            github_url=existing.github_url if existing else None,
            portfolio_url=existing.portfolio_url if existing else None,
            ai_consent_given=existing.ai_consent_given if existing else True,
            notification_consent=existing.notification_consent if existing else False,
        )
        updated = await self._profile_service.update_profile(user=self._user, payload=payload)
        return {
            "updated": True,
            "headline": updated.headline,
            "target_roles": updated.target_roles,
            "preferred_locations": updated.preferred_locations,
        }

    async def _search_jobs(self, args: dict[str, Any]) -> dict[str, Any]:
        response = await self._job_discovery.search_jobs(
            user=self._user,
            q=str(args.get("query") or ""),
            location=args.get("location"),
            work_mode=args.get("work_mode"),
            experience_level=args.get("experience_level"),
            refresh=bool(args.get("refresh", bool(self._settings.openai_api_key.strip()))),
            limit=int(args.get("limit") or 5),
        )
        return {
            "total": response.total,
            "source": response.source,
            "jobs": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "company": item.company,
                    "location": item.location,
                    "work_mode": item.work_mode,
                    "external_url": item.external_url,
                    "match_score": (
                        item.match_preview.overall_score if item.match_preview else None
                    ),
                }
                for item in response.items
            ],
        }

    async def _calculate_job_match(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = _parse_uuid(args.get("job_id"), "job_id")
        match = await self._job_matching.calculate_match_for_job(
            user=self._user,
            job_id=job_id,
            use_semantic=bool(self._settings.openai_api_key.strip()),
        )
        return match.model_dump(mode="json")

    async def _generate_tailored_document(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = _parse_uuid(args.get("job_id"), "job_id")
        resume_id = _parse_uuid(args["resume_id"], "resume_id") if args.get("resume_id") else None
        doc_type = str(args.get("document_type") or "tailored_resume")
        focus = args.get("focus_instructions")
        if doc_type == "tailored_resume":
            doc = await self._documents.tailor_resume(
                user=self._user,
                payload=TailorResumeRequest(
                    job_id=job_id,
                    resume_id=resume_id,
                    focus_instructions=focus,
                ),
            )
        elif doc_type == "cover_letter":
            doc = await self._documents.generate_cover_letter(
                user=self._user,
                payload=CoverLetterRequest(
                    job_id=job_id,
                    resume_id=resume_id,
                    custom_notes=focus,
                ),
            )
        else:
            doc = await self._documents.generate_application_note(
                user=self._user,
                payload=ApplicationNoteRequest(job_id=job_id, resume_id=resume_id),
            )
        return {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "title": doc.title,
            "version": doc.version,
            "is_grounded": bool(doc.factuality_report.get("is_grounded", False)),
            "preview": doc.content_markdown[:500],
        }

    async def _list_applications(self, args: dict[str, Any]) -> dict[str, Any]:
        status = args.get("status")
        listed = await self._applications.list_applications(
            user_id=self._user.id,
            status=str(status) if status else None,
            limit=25,
        )
        summary = await self._applications.get_summary(user_id=self._user.id)
        return {
            "total": listed.total,
            "counts_by_status": summary.counts_by_status,
            "items": [
                {
                    "id": str(item.id),
                    "job_id": str(item.job_id) if item.job_id else None,
                    "company_name": item.company_name,
                    "role_title": item.role_title,
                    "status": item.status,
                    "deadline_at": item.deadline_at,
                    "allowed_next_statuses": item.allowed_next_statuses,
                }
                for item in listed.items
            ],
        }

    async def _create_or_update_application(self, args: dict[str, Any]) -> dict[str, Any]:
        if args.get("transition_to") in ("SUBMITTED", "AWAITING_APPROVAL"):
            return {
                "requires_approval": True,
                "message": "External submission requires human confirmation. "
                "Call prepare_application_submission instead.",
            }

        app_id = (
            _parse_uuid(args["application_id"], "application_id")
            if args.get("application_id")
            else None
        )
        job_id = _parse_uuid(args["job_id"], "job_id") if args.get("job_id") else None

        if app_id is None and job_id is not None:
            existing = await self._apps_repo.get_by_user_and_job(
                user_id=self._user.id,
                job_id=job_id,
            )
            if existing is not None:
                app_id = existing.id

        if app_id is None:
            detail = await self._applications.create_application(
                user_id=self._user.id,
                payload=ApplicationCreateRequest(
                    job_id=job_id,
                    company_name=args.get("company_name"),
                    role_title=args.get("role_title"),
                    job_url=args.get("job_url"),
                    location=args.get("location"),
                    deadline_at=_parse_optional_dt(args.get("deadline_at")),
                    follow_up_at=_parse_optional_dt(args.get("follow_up_at")),
                    notes=args.get("notes"),
                ),
            )
        else:
            detail = await self._applications.update_application(
                user_id=self._user.id,
                application_id=app_id,
                payload=ApplicationUpdateRequest(
                    company_name=args.get("company_name"),
                    role_title=args.get("role_title"),
                    job_url=args.get("job_url"),
                    location=args.get("location"),
                    deadline_at=_parse_optional_dt(args.get("deadline_at")),
                    follow_up_at=_parse_optional_dt(args.get("follow_up_at")),
                    notes=args.get("notes"),
                ),
            )

        if args.get("transition_to"):
            detail = await self._applications.transition_status(
                user_id=self._user.id,
                application_id=detail.id,
                payload=ApplicationTransitionRequest(
                    target_status=str(args["transition_to"]),
                    note=args.get("transition_note"),
                ),
            )

        return detail.model_dump(mode="json", exclude={"history"})

    async def _prepare_application_submission(self, args: dict[str, Any]) -> dict[str, Any]:
        app_id = (
            _parse_uuid(args["application_id"], "application_id")
            if args.get("application_id")
            else None
        )
        job_id = _parse_uuid(args["job_id"], "job_id") if args.get("job_id") else None

        if app_id is None and job_id is not None:
            existing = await self._apps_repo.get_by_user_and_job(
                user_id=self._user.id, job_id=job_id
            )
            if existing is None:
                created = await self._applications.create_application(
                    user_id=self._user.id,
                    payload=ApplicationCreateRequest(job_id=job_id, notes=args.get("notes")),
                )
                app_id = created.id
            else:
                app_id = existing.id

        if app_id is None:
            raise ValueError("Provide application_id or job_id to prepare submission approval.")

        app_detail = await self._applications.get_application(
            user_id=self._user.id, application_id=app_id
        )
        destination = app_detail.job_url or f"{app_detail.company_name} Application Portal"
        approval = await self._approvals.create_approval(
            user_id=self._user.id,
            payload=ApprovalCreateRequest(
                action_type="submit_application",
                application_id=app_detail.id,
                target_destination=destination,
                title=f"Submit Application: {app_detail.role_title} at {app_detail.company_name}",
                payload={
                    "company": app_detail.company_name,
                    "role": app_detail.role_title,
                    "tailored_resume_id": (
                        str(app_detail.tailored_resume_id)
                        if app_detail.tailored_resume_id
                        else None
                    ),
                    "cover_letter_id": (
                        str(app_detail.cover_letter_id) if app_detail.cover_letter_id else None
                    ),
                    "notes": args.get("notes") or app_detail.notes,
                },
            ),
        )
        self.created_approval_ids.append(str(approval.id))
        return {
            "approval_id": str(approval.id),
            "status": approval.status,
            "title": approval.title,
            "target_destination": approval.target_destination,
            "application_id": str(app_detail.id),
        }

    async def _list_pending_approvals(self, args: dict[str, Any]) -> dict[str, Any]:
        status = args.get("status")
        listed = await self._approvals.list_approvals(
            user_id=self._user.id,
            status=str(status) if status else None,
            limit=20,
        )
        return {
            "pending_count": listed.pending_count,
            "items": [
                {
                    "id": str(item.id),
                    "action_type": item.action_type,
                    "title": item.title,
                    "status": item.status,
                    "target_destination": item.target_destination,
                }
                for item in listed.items
            ],
        }

    async def _sync_career_knowledge(self, _args: dict[str, Any]) -> dict[str, Any]:
        res = await self._rag.index_user_career_context(user_id=self._user.id)
        return {
            "indexed_chunks": res.indexed_chunks,
            "skipped_duplicates": res.skipped_duplicates,
            "source_counts": res.source_counts,
        }

    async def _query_career_knowledge(self, args: dict[str, Any]) -> dict[str, Any]:
        hits = await self._rag.retrieve_context(
            user_id=self._user.id,
            query=str(args.get("query") or ""),
            top_k=int(args.get("top_k") or 5),
        )
        return {
            "hits": [
                {
                    "label": h.metadata.get("label"),
                    "source_type": h.metadata.get("source_type"),
                    "score": h.score,
                    "text": h.text,
                }
                for h in hits
            ]
        }

    async def _list_calendar_events(self, args: dict[str, Any]) -> dict[str, Any]:
        res = await self._calendar.list_upcoming_events(
            user_id=self._user.id,
            days_ahead=int(args.get("days_ahead") or 7),
            max_results=int(args.get("max_results") or 50),
        )
        if not res.connected:
            return {
                "connected": False,
                "message": "Google Calendar is not connected yet. Ask the user to click "
                "'Connect Google Calendar' in the AI Co-Pilot sidebar.",
            }
        return res.model_dump(mode="json")

    async def _propose_calendar_event(self, args: dict[str, Any]) -> dict[str, Any]:
        status = await self._calendar.get_status(user_id=self._user.id)
        if not status.connected:
            return {
                "connected": False,
                "message": "Google Calendar is not connected yet. Ask the user to click "
                "'Connect Google Calendar' in the AI Co-Pilot sidebar before scheduling events.",
            }

        summary = str(args.get("summary") or "").strip()
        start_iso = str(args.get("start_iso") or "").strip()
        end_iso = str(args.get("end_iso") or "").strip()
        if not summary or not start_iso or not end_iso:
            raise ValueError("summary, start_iso, and end_iso are required.")

        tz = str(args.get("timezone") or self._user.timezone or "UTC")
        approval = await self._approvals.create_approval(
            user_id=self._user.id,
            payload=ApprovalCreateRequest(
                action_type="create_calendar_event",
                target_destination=f"Google Calendar ({status.google_email or 'primary'})",
                title=f"Schedule Calendar Event: {summary}"[:250],
                payload={
                    "summary": summary,
                    "start_iso": start_iso,
                    "end_iso": end_iso,
                    "description": args.get("description"),
                    "location": args.get("location"),
                    "timezone": tz,
                },
            ),
        )
        self.created_approval_ids.append(str(approval.id))
        return {
            "approval_id": str(approval.id),
            "status": approval.status,
            "title": approval.title,
            "summary": summary,
            "start_iso": start_iso,
            "end_iso": end_iso,
            "timezone": tz,
            "message": "Calendar event prepared and awaiting user confirmation button click.",
        }

    async def _list_interview_sessions(self, args: dict[str, Any]) -> dict[str, Any]:
        res = await self._interviews.list_sessions(
            user=self._user, limit=int(args.get("limit") or 10)
        )
        return res.model_dump(mode="json")

    async def _get_skill_gap_plan(self, _args: dict[str, Any]) -> dict[str, Any]:
        plan = await self._interviews.get_skill_gap_plan(user=self._user)
        return plan.model_dump(mode="json")

    async def _list_career_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        res = await self._memory.list_memories(
            user=self._user, approved_only=bool(args.get("approved_only", False))
        )
        return res.model_dump(mode="json")

    async def _save_career_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        entry = await self._memory.create_memory(
            user=self._user,
            payload=CareerMemoryCreateRequest(
                category=args.get("category") or "note",
                title=str(args["title"]),
                content=str(args["content"]),
                source="copilot_proposed",
                memory_key=args.get("memory_key"),
            ),
        )
        return entry.model_dump(mode="json")

    async def _list_reminders(self, args: dict[str, Any]) -> dict[str, Any]:
        res = await self._reminders.list_reminders(
            user=self._user, status=args.get("status")
        )
        return res.model_dump(mode="json")

    async def _schedule_reminder(self, args: dict[str, Any]) -> dict[str, Any]:
        dt = datetime.fromisoformat(str(args["scheduled_for"]).replace("Z", "+00:00"))
        created = await self._reminders.create_reminder(
            user=self._user,
            payload=ReminderCreateRequest(
                title=str(args["title"]),
                message=args.get("message"),
                reminder_type=args.get("reminder_type") or "custom",
                dedup_key=args.get("dedup_key"),
                scheduled_for=dt,
                timezone=args.get("timezone") or self._user.timezone,
            ),
        )
        return created.model_dump(mode="json")
