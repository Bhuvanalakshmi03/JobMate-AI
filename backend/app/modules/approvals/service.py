"""Human approval enforcement service preventing unapproved external actions."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.database.base import utc_now
from app.modules.applications.repository import ApplicationRepository
from app.modules.applications.schemas import ApplicationTransitionRequest
from app.modules.applications.service import ApplicationService
from app.modules.approvals.models import ApprovalRequest
from app.modules.approvals.repository import ApprovalRepository
from app.modules.approvals.schemas import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)
from app.modules.authentication.repository import UserRepository
from app.modules.calendar.schemas import CalendarEventCreateRequest
from app.modules.calendar.service import CalendarService
from app.repositories.audit_repository import AuditLogRepository

WorkflowDecisionHook = Callable[[ApprovalRequest, str], Awaitable[None]]


class ApprovalService:
    """Enforces mandatory human approval before external application or outreach actions."""

    def __init__(
        self,
        session: AsyncSession,
        workflow_hook: WorkflowDecisionHook | None = None,
        settings: Settings | None = None,
        calendar_service: CalendarService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._approvals = ApprovalRepository(session)
        self._apps = ApplicationRepository(session)
        self._app_service = ApplicationService(session)
        self._users = UserRepository(session)
        self._calendar = calendar_service or CalendarService(
            session=session, settings=self._settings
        )
        self._audit = AuditLogRepository(session)
        self._workflow_hook = workflow_hook

    async def create_approval(
        self,
        *,
        user_id: uuid.UUID,
        payload: ApprovalCreateRequest,
        workflow_run_id: uuid.UUID | None = None,
    ) -> ApprovalResponse:
        if payload.application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=payload.application_id,
                user_id=user_id,
            )
            if app is None:
                raise NotFoundError("Application not found.")

            if payload.action_type == "submit_application":
                if app.status == "SAVED":
                    await self._app_service.transition_status(
                        user_id=user_id,
                        application_id=app.id,
                        payload=ApplicationTransitionRequest(
                            target_status="PREPARING",
                            note="Prepared for approval request",
                        ),
                    )
                    app = await self._apps.get_by_id_for_user(
                        application_id=app.id, user_id=user_id
                    )
                if app is not None and app.status == "PREPARING":
                    await self._app_service.transition_status(
                        user_id=user_id,
                        application_id=app.id,
                        payload=ApplicationTransitionRequest(
                            target_status="AWAITING_APPROVAL",
                            note=f"Approval requested: {payload.title}",
                        ),
                    )
                elif app is not None and app.status != "AWAITING_APPROVAL":
                    raise ValidationError(
                        "Cannot request submission approval while application is in "
                        f"'{app.status}'."
                    )

        record = await self._approvals.create(
            user_id=user_id,
            workflow_run_id=workflow_run_id,
            application_id=payload.application_id,
            action_type=payload.action_type,
            target_destination=payload.target_destination.strip(),
            title=payload.title.strip(),
            payload=dict(payload.payload),
        )
        await self._audit.record(
            event_type="approval.requested",
            user_id=user_id,
            resource_type="approval",
            resource_id=str(record.id),
            details={
                "action_type": record.action_type,
                "target_destination": record.target_destination,
                "application_id": str(record.application_id) if record.application_id else None,
                "workflow_run_id": str(record.workflow_run_id) if record.workflow_run_id else None,
            },
        )
        return ApprovalResponse.model_validate(record)

    async def list_approvals(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ApprovalListResponse:
        rows, total, pending_count = await self._approvals.list_for_user(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return ApprovalListResponse(
            items=[ApprovalResponse.model_validate(item) for item in rows],
            total=total,
            pending_count=pending_count,
        )

    async def get_approval(
        self,
        *,
        user_id: uuid.UUID,
        approval_id: uuid.UUID,
    ) -> ApprovalResponse:
        record = await self._approvals.get_by_id_for_user(
            approval_id=approval_id,
            user_id=user_id,
        )
        if record is None:
            raise NotFoundError("Approval request not found.")
        return ApprovalResponse.model_validate(record)

    async def approve(
        self,
        *,
        user_id: uuid.UUID,
        approval_id: uuid.UUID,
        decision: ApprovalDecisionRequest,
    ) -> ApprovalResponse:
        record = await self._approvals.get_by_id_for_user(
            approval_id=approval_id,
            user_id=user_id,
        )
        if record is None:
            raise NotFoundError("Approval request not found.")
        if record.status != "PENDING":
            raise ValidationError(
                f"Approval request has already been decided (status: {record.status})."
            )

        now = utc_now()
        trimmed_note = decision.note.strip() if decision.note and decision.note.strip() else None
        record.status = "APPROVED"
        record.decided_at = now
        record.decision_note = trimmed_note
        await self._session.flush()

        await self._audit.record(
            event_type="approval.approved",
            user_id=user_id,
            resource_type="approval",
            resource_id=str(record.id),
            details={"action_type": record.action_type, "note": record.decision_note},
        )

        # Resume linked agent workflow if present before finalizing execution receipt.
        if self._workflow_hook is not None and record.workflow_run_id is not None:
            await self._workflow_hook(record, "APPROVED")

        execution_summary = await self._execute_approved_action(user_id=user_id, record=record)
        record.status = "EXECUTED"
        record.executed_at = utc_now()
        record.execution_result = execution_summary
        await self._session.flush()
        await self._session.refresh(record)

        await self._audit.record(
            event_type="approval.executed",
            user_id=user_id,
            resource_type="approval",
            resource_id=str(record.id),
            details=execution_summary,
        )
        return ApprovalResponse.model_validate(record)

    async def _execute_approved_action(
        self,
        *,
        user_id: uuid.UUID,
        record: ApprovalRequest,
    ) -> dict[str, Any]:
        """Execute verified post-approval action safely without inventing unapproved changes."""
        if record.status != "APPROVED":
            raise ValidationError("External execution requires explicit APPROVED status.")

        if record.action_type == "create_calendar_event":
            owner = await self._users.get_by_id(user_id)
            if owner is None:
                raise NotFoundError("Approving user account was not found.")
            raw_payload = dict(record.payload or {})
            event = await self._calendar.create_event(
                user=owner,
                payload=CalendarEventCreateRequest(
                    summary=str(raw_payload.get("summary") or record.title)[:250],
                    start_iso=str(raw_payload.get("start_iso") or ""),
                    end_iso=str(raw_payload.get("end_iso") or ""),
                    description=(
                        str(raw_payload["description"])
                        if raw_payload.get("description")
                        else None
                    ),
                    location=(
                        str(raw_payload["location"]) if raw_payload.get("location") else None
                    ),
                    timezone=(
                        str(raw_payload["timezone"]) if raw_payload.get("timezone") else None
                    ),
                ),
            )
            return {
                "executed": True,
                "action_type": record.action_type,
                "target_destination": record.target_destination,
                "event_id": event.event_id,
                "html_link": event.html_link,
                "start_iso": event.start_iso,
                "end_iso": event.end_iso,
                "mode": "google_calendar_api_v3",
            }

        application_transitioned = False
        if record.action_type == "submit_application" and record.application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=record.application_id,
                user_id=user_id,
            )
            if app is not None and app.status == "AWAITING_APPROVAL":
                await self._app_service.transition_status(
                    user_id=user_id,
                    application_id=app.id,
                    payload=ApplicationTransitionRequest(
                        target_status="SUBMITTED",
                        note=record.decision_note or f"Approved action: {record.title}",
                    ),
                )
                application_transitioned = True

        return {
            "executed": True,
            "action_type": record.action_type,
            "target_destination": record.target_destination,
            "application_id": str(record.application_id) if record.application_id else None,
            "application_transitioned_to_submitted": application_transitioned,
            "mode": "recorded_confirmed_dispatch",
        }

    async def reject(
        self,
        *,
        user_id: uuid.UUID,
        approval_id: uuid.UUID,
        decision: ApprovalDecisionRequest,
    ) -> ApprovalResponse:
        record = await self._approvals.get_by_id_for_user(
            approval_id=approval_id,
            user_id=user_id,
        )
        if record is None:
            raise NotFoundError("Approval request not found.")
        if record.status != "PENDING":
            raise ValidationError(
                f"Approval request has already been decided (status: {record.status})."
            )

        trimmed_note = decision.note.strip() if decision.note and decision.note.strip() else None
        record.status = "REJECTED"
        record.decided_at = utc_now()
        record.decision_note = trimmed_note
        await self._session.flush()

        if record.action_type == "submit_application" and record.application_id is not None:
            app = await self._apps.get_by_id_for_user(
                application_id=record.application_id,
                user_id=user_id,
            )
            if app is not None and app.status == "AWAITING_APPROVAL":
                await self._app_service.transition_status(
                    user_id=user_id,
                    application_id=app.id,
                    payload=ApplicationTransitionRequest(
                        target_status="PREPARING",
                        note=record.decision_note or "Submission approval rejected by user",
                    ),
                )

        if self._workflow_hook is not None and record.workflow_run_id is not None:
            await self._workflow_hook(record, "REJECTED")

        await self._session.refresh(record)
        await self._audit.record(
            event_type="approval.rejected",
            user_id=user_id,
            resource_type="approval",
            resource_id=str(record.id),
            details={"action_type": record.action_type, "note": record.decision_note},
        )
        return ApprovalResponse.model_validate(record)
