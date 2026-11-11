"""Agent execution guardrails, retry policies, token limits, and trace recording."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from app.agents.state import CareerPilotAgentState
from app.core.exceptions import (
    ExternalServiceError,
    ValidationError,
)
from app.core.exceptions import (
    RateLimitError as AppRateLimitError,
)

T = TypeVar("T")

MAX_WORKFLOW_STEPS = 12
DEFAULT_TOKEN_BUDGET = 24000
MAX_NODE_RETRIES = 2

_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ExternalServiceError,
    AppRateLimitError,
    TimeoutError,
    asyncio.TimeoutError,
)


def append_trace(
    existing: list[dict[str, Any]],
    *,
    node: str,
    status: str,
    attempts: int,
    duration_ms: float,
    tokens_used: int = 0,
    detail: str | None = None,
) -> list[dict[str, Any]]:
    """Return a new trace list appending an immutable step execution entry."""
    entry = {
        "node": node,
        "status": status,
        "attempts": attempts,
        "duration_ms": round(duration_ms, 2),
        "tokens_used": tokens_used,
        "detail": detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return [*existing, entry]


async def run_with_retry_policy(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = MAX_NODE_RETRIES,
    base_delay_seconds: float = 0.05,
) -> tuple[T, int]:
    """Execute an async agent step with bounded retries on transient service failures."""
    last_exc: Exception | None = None
    attempts = 0
    for attempt in range(1, max_retries + 2):
        attempts = attempt
        try:
            result = await operation()
            return result, attempts
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt <= max_retries:
                await asyncio.sleep(base_delay_seconds * attempt)
                continue
            raise
    raise ExternalServiceError("Agent step exhausted retries.") from last_exc


def enforce_workflow_budgets(*, step_count: int, total_tokens_used: int, max_tokens: int) -> None:
    """Enforce maximum graph steps and LLM token consumption per workflow run."""
    if step_count >= MAX_WORKFLOW_STEPS:
        raise ValidationError(
            f"Agent workflow step limit exceeded (max {MAX_WORKFLOW_STEPS} steps)."
        )
    if total_tokens_used > max_tokens:
        raise ValidationError(
            f"Agent workflow token budget exceeded ({total_tokens_used} > {max_tokens})."
        )


def monotonic_ms(start_perf: float) -> float:
    return (time.perf_counter() - start_perf) * 1000.0


@dataclass(frozen=True, slots=True)
class TracedStepOutcome(Generic[T]):
    """Outcome of a policy-guarded node invocation including tokens and state failure patch."""

    ok: bool
    value: T | None = None
    tokens_used: int = 0
    attempts: int = 1
    duration_ms: float = 0.0
    trace: list[dict[str, Any]] | None = None
    error_message: str | None = None


async def execute_traced_step(
    state: CareerPilotAgentState,
    *,
    node: str,
    operation: Callable[[], Awaitable[T]],
    token_extractor: Callable[[T], int] | None = None,
    detail: str | None = None,
    max_tokens: int = DEFAULT_TOKEN_BUDGET,
    retryable: bool = True,
) -> TracedStepOutcome[T]:
    """Execute one specialist node under step/token limits, retry policy, and tracing."""
    start = time.perf_counter()
    existing_trace = list(state.get("execution_trace", []))
    current_steps = int(state.get("step_count", 0))
    current_tokens = int(state.get("total_tokens_used", 0))

    try:
        enforce_workflow_budgets(
            step_count=current_steps,
            total_tokens_used=current_tokens,
            max_tokens=max_tokens,
        )
        if retryable:
            value, attempts = await run_with_retry_policy(operation)
        else:
            value = await operation()
            attempts = 1
        step_tokens = token_extractor(value) if token_extractor is not None else 0
        duration = monotonic_ms(start)
        status = "recovered" if attempts > 1 else "completed"
        updated_trace = append_trace(
            existing_trace,
            node=node,
            status=status,
            attempts=attempts,
            duration_ms=duration,
            tokens_used=step_tokens,
            detail=detail,
        )
        return TracedStepOutcome(
            ok=True,
            value=value,
            tokens_used=step_tokens,
            attempts=attempts,
            duration_ms=duration,
            trace=updated_trace,
        )
    except Exception as exc:
        duration = monotonic_ms(start)
        err_msg = str(exc) or exc.__class__.__name__
        updated_trace = append_trace(
            existing_trace,
            node=node,
            status="failed",
            attempts=1,
            duration_ms=duration,
            tokens_used=0,
            detail=err_msg,
        )
        return TracedStepOutcome(
            ok=False,
            value=None,
            tokens_used=0,
            attempts=1,
            duration_ms=duration,
            trace=updated_trace,
            error_message=err_msg,
        )
