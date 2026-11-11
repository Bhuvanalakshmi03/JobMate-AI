"""Application tracking business logic, ownership validation, and state transitions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.database.base import utc_now
from app.modules.applications.models import Application
from app.modules.applications.repository import ApplicationRepository
from app.modules.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationHistoryItem,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationSummaryResponse,
    ApplicationTransitionRequest,
    ApplicationUpdateRequest,
)
from app.modules.applications.state_machine import (
    ALL_APPLICATION_STATUSES,
    get_allowed_transitions,
    validate_status_transition,
)
from app.modules.documents.repository import DocumentRepository
from app.modules.jobs.repository import JobRepository
from app.repositories.audit_repository import AuditLogRepository


def _normalize_utc_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class ApplicationService:
    """Manages student job applications, controlled status transitions, and history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._apps = ApplicationRepository(session)
        self._jobs = JobRepository(session)
        self._docs = DocumentRepository(session)
        self._audit = AuditLogRepository(session)

    def _to_response(self, app: Application) -> ApplicationResponse:
        return ApplicationResponse(
            id=app.id,
            user_id=app.user_id,
            job_id=app.job_id,
            tailored_resume_id=app.tailored_resume_id,
            cover_letter_id=app.cover_letter_id,
            company_name=app.company_name,
            role_title=app.role_title,
            job_url=app.job_url,
            location=app.location,
            status=app.status,
            allowed_next_statuses=get_allowed_transitions(app.status),
            applied_at=app.applied_at,
            deadline_at=app.deadline_at,
            follow_up_at=app.follow_up_at,
            notes=app.notes,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )

    async def _require_owned_application(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> Application:
        app = await self._apps.get_by_id_for_user(
            application_id=application_id,
            user_id=user_id,
        )
        if app is None:
            raise NotFoundError("Application not found.")
        return app

    async def _validate_owned_documents(
        self,
        *,
        user_id: uuid.UUID,
        tailored_resume_id: uuid.UUID | None,
        cover_letter_id: uuid.UUID | None,
    ) -> None:
        if tailored_resume_id is not None:
            doc = await self._docs.get_by_id_for_user(
                document_id=tailored_resume_id,
                user_id=user_id,
            )
            if doc is None:
                raise NotFoundError("Tailored resume document not found.")
        if cover_letter_id is not None:
            doc = await self._docs.get_by_id_for_user(
                document_id=cover_letter_id,
                user_id=user_id,
            )
            if doc is None:
                raise NotFoundError("Cover letter document not found.")

    async def create_application(
        self,
        *,
        user_id: uuid.UUID,
        payload: ApplicationCreateRequest,
    ) -> ApplicationDetailResponse:
        company_name = (payload.company_name or "").strip()
        role_title = (payload.role_title or "").strip()
        job_url = payload.job_url
        location = payload.location.strip() if payload.location else None

        if payload.job_id is not None:
            job = await self._jobs.get_by_id(payload.job_id)
            if job is None:
                raise NotFoundError("Referenced job listing not found.")
            existing = await self._apps.get_by_user_and_job(
                user_id=user_id,
                job_id=payload.job_id,
            )
            if existing is not None:
                raise ConflictError("An application for this job already exists.")
            company_name = company_name or job.company
            role_title = role_title or job.title
            job_url = job_url or job.external_url
            location = location or job.location
        elif not company_name or not role_title:
            raise ValidationError(
                "company_name and role_title are required when job_id is not provided."
            )

        await self._validate_owned_documents(
            user_id=user_id,
            tailored_resume_id=payload.tailored_resume_id,
            cover_letter_id=payload.cover_letter_id,
        )

        app = await self._apps.create(
            user_id=user_id,
            job_id=payload.job_id,
            tailored_resume_id=payload.tailored_resume_id,
            cover_letter_id=payload.cover_letter_id,
            company_name=company_name[:255],
            role_title=role_title[:255],
            job_url=job_url,
            location=location[:255] if location else None,
            deadline_at=_normalize_utc_datetime(payload.deadline_at),
            follow_up_at=_normalize_utc_datetime(payload.follow_up_at),
            notes=payload.notes.strip() if payload.notes else None,
        )
        history_entry = await self._apps.add_history(
            application_id=app.id,
            user_id=user_id,
            from_status=None,
            to_status="SAVED",
            note="Application added to tracker",
        )
        await self._audit.record(
            event_type="applications.created",
            user_id=user_id,
            resource_type="application",
            resource_id=str(app.id),
            details={"job_id": str(payload.job_id) if payload.job_id else None},
        )
        base = self._to_response(app)
        return ApplicationDetailResponse(
            **base.model_dump(),
            history=[ApplicationHistoryItem.model_validate(history_entry)],
        )

    async def list_applications(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ApplicationListResponse:
        rows, total = await self._apps.list_for_user(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return ApplicationListResponse(
            items=[self._to_response(row) for row in rows],
            total=total,
        )

    async def get_application(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> ApplicationDetailResponse:
        app = await self._require_owned_application(user_id=user_id, application_id=application_id)
        history = await self._apps.list_history(application_id=app.id, user_id=user_id)
        base = self._to_response(app)
        return ApplicationDetailResponse(
            **base.model_dump(),
            history=[ApplicationHistoryItem.model_validate(item) for item in history],
        )

    async def update_application(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        payload: ApplicationUpdateRequest,
    ) -> ApplicationDetailResponse:
        app = await self._require_owned_application(user_id=user_id, application_id=application_id)
        fields_set = payload.model_fields_set

        await self._validate_owned_documents(
            user_id=user_id,
            tailored_resume_id=(
                payload.tailored_resume_id if "tailored_resume_id" in fields_set else None
            ),
            cover_letter_id=payload.cover_letter_id if "cover_letter_id" in fields_set else None,
        )

        if "company_name" in fields_set and payload.company_name:
            app.company_name = payload.company_name.strip()[:255]
        if "role_title" in fields_set and payload.role_title:
            app.role_title = payload.role_title.strip()[:255]
        if "job_url" in fields_set:
            app.job_url = payload.job_url
        if "location" in fields_set:
            app.location = payload.location.strip()[:255] if payload.location else None
        if "tailored_resume_id" in fields_set:
            app.tailored_resume_id = payload.tailored_resume_id
        if "cover_letter_id" in fields_set:
            app.cover_letter_id = payload.cover_letter_id
        if "deadline_at" in fields_set:
            app.deadline_at = _normalize_utc_datetime(payload.deadline_at)
        if "follow_up_at" in fields_set:
            app.follow_up_at = _normalize_utc_datetime(payload.follow_up_at)
        if "notes" in fields_set:
            app.notes = payload.notes.strip() if payload.notes else None

        await self._session.flush()
        await self._audit.record(
            event_type="applications.updated",
            user_id=user_id,
            resource_type="application",
            resource_id=str(app.id),
        )
        return await self.get_application(user_id=user_id, application_id=app.id)

    async def transition_status(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        payload: ApplicationTransitionRequest,
    ) -> ApplicationDetailResponse:
        app = await self._require_owned_application(user_id=user_id, application_id=application_id)
        previous_status = app.status
        validate_status_transition(
            current_status=previous_status,
            target_status=payload.target_status,
        )

        app.status = payload.target_status
        if payload.target_status == "SUBMITTED" and app.applied_at is None:
            app.applied_at = utc_now()

        await self._apps.add_history(
            application_id=app.id,
            user_id=user_id,
            from_status=previous_status,
            to_status=payload.target_status,
            note=payload.note.strip() if payload.note else None,
        )
        await self._session.flush()
        await self._audit.record(
            event_type="applications.transitioned",
            user_id=user_id,
            resource_type="application",
            resource_id=str(app.id),
            details={"from": previous_status, "to": payload.target_status},
        )
        return await self.get_application(user_id=user_id, application_id=app.id)

    async def delete_application(
        self,
        *,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> None:
        app = await self._require_owned_application(user_id=user_id, application_id=application_id)
        await self._apps.delete_record(app)
        await self._audit.record(
            event_type="applications.deleted",
            user_id=user_id,
            resource_type="application",
            resource_id=str(application_id),
        )

    async def get_summary(self, *, user_id: uuid.UUID) -> ApplicationSummaryResponse:
        apps = await self._apps.list_all_for_summary(user_id=user_id)
        counts: dict[str, int] = {status: 0 for status in ALL_APPLICATION_STATUSES}
        now = utc_now()
        upcoming: list[Application] = []

        for app in apps:
            counts[app.status] = counts.get(app.status, 0) + 1
            if (
                app.deadline_at is not None
                and app.status not in ("REJECTED", "WITHDRAWN", "OFFER_RECEIVED")
                and app.deadline_at >= now
            ):
                upcoming.append(app)

        upcoming.sort(key=lambda item: item.deadline_at or now)
        return ApplicationSummaryResponse(
            total_applications=len(apps),
            counts_by_status=counts,
            upcoming_deadlines=[self._to_response(item) for item in upcoming[:5]],
        )
