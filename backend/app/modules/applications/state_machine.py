"""Controlled state machine governing application status transitions."""

from __future__ import annotations

from typing import Literal

from app.core.exceptions import ValidationError

ApplicationStatus = Literal[
    "SAVED",
    "PREPARING",
    "AWAITING_APPROVAL",
    "SUBMITTED",
    "INTERVIEW_SCHEDULED",
    "REJECTED",
    "OFFER_RECEIVED",
    "WITHDRAWN",
]

ALL_APPLICATION_STATUSES: tuple[ApplicationStatus, ...] = (
    "SAVED",
    "PREPARING",
    "AWAITING_APPROVAL",
    "SUBMITTED",
    "INTERVIEW_SCHEDULED",
    "REJECTED",
    "OFFER_RECEIVED",
    "WITHDRAWN",
)

ALLOWED_TRANSITIONS: dict[str, tuple[ApplicationStatus, ...]] = {
    "SAVED": ("PREPARING", "WITHDRAWN"),
    "PREPARING": ("AWAITING_APPROVAL", "SAVED", "WITHDRAWN"),
    "AWAITING_APPROVAL": ("SUBMITTED", "PREPARING", "WITHDRAWN"),
    "SUBMITTED": ("INTERVIEW_SCHEDULED", "REJECTED", "OFFER_RECEIVED", "WITHDRAWN"),
    "INTERVIEW_SCHEDULED": ("OFFER_RECEIVED", "REJECTED", "WITHDRAWN"),
    "OFFER_RECEIVED": ("WITHDRAWN",),
    "REJECTED": (),
    "WITHDRAWN": (),
}


def get_allowed_transitions(current_status: str) -> list[ApplicationStatus]:
    """Return valid next statuses from the given current status."""
    return list(ALLOWED_TRANSITIONS.get(current_status, ()))


def validate_status_transition(*, current_status: str, target_status: str) -> None:
    """Enforce valid application state transitions on the backend."""
    if current_status == target_status:
        raise ValidationError(f"Application is already in status '{current_status}'.")
    allowed = ALLOWED_TRANSITIONS.get(current_status)
    if allowed is None:
        raise ValidationError(f"Unknown current application status: '{current_status}'.")
    if target_status not in allowed:
        allowed_str = ", ".join(allowed) if allowed else "none (terminal state)"
        raise ValidationError(
            f"Invalid status transition from '{current_status}' to '{target_status}'. "
            f"Allowed next statuses: {allowed_str}."
        )
