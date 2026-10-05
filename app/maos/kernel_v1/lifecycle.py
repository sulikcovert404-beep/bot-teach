"""Pure guarded task lifecycle transition function."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TaskState(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    PLANNED = "planned"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    SUCCEEDED = "succeeded"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    BLOCKED = "blocked"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class TaskEvent(StrEnum):
    VALIDATE = "validate"
    PLAN = "plan"
    DISPATCH = "dispatch"
    START = "start"
    SUBMIT_FOR_REVIEW = "submit_for_review"
    REVIEW_APPROVE = "review_approve"
    REVIEW_REJECT = "review_reject"
    FAIL_RETRYABLE = "fail_retryable"
    FAIL_TERMINAL = "fail_terminal"
    BLOCK = "block"
    RESUME = "resume"
    CANCEL = "cancel"
    CONFIRM_CANCEL = "confirm_cancel"


class TransitionRejected(ValueError):
    """Raised when an event cannot legally move the current task state."""


@dataclass(frozen=True, slots=True)
class TransitionContext:
    acceptance_met: bool = False
    verifier_receipt: str | None = None
    evidence_receipts: tuple[str, ...] = ()
    classified_transient_failure: bool = False
    attempt_budget_remaining: bool = False
    material_change_or_reassignment: bool = False
    blocker_resolution_ref: str | None = None
    references_revalidated: bool = False
    new_attempt_planned: bool = False
    effect_running: bool = False
    effect_reconciled: bool = False
    cancellation_resolution_ref: str | None = None
    completion_operation_id: str | None = None
    completion_idempotency_key: str | None = None
    bound_operation_id: str | None = None
    bound_idempotency_key: str | None = None
    attempt_generation: int | None = None
    result_generation: int | None = None


@dataclass(frozen=True, slots=True)
class TaskTransitionRecord:
    event_id: str
    task_id: str
    event: TaskEvent
    from_state: TaskState
    to_state: TaskState
    occurred_at: datetime
    fingerprint: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskAggregate:
    task_id: str
    state: TaskState
    history: tuple[TaskTransitionRecord, ...] = ()


class EventIdentityConflict(ValueError):
    """An event id was reused for different content."""


_TRANSITIONS: dict[TaskState, dict[TaskEvent, TaskState]] = {
    TaskState.CREATED: {TaskEvent.VALIDATE: TaskState.VALIDATED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.VALIDATED: {TaskEvent.PLAN: TaskState.PLANNED, TaskEvent.BLOCK: TaskState.BLOCKED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.PLANNED: {TaskEvent.DISPATCH: TaskState.DISPATCHED, TaskEvent.BLOCK: TaskState.BLOCKED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.DISPATCHED: {TaskEvent.START: TaskState.RUNNING, TaskEvent.BLOCK: TaskState.BLOCKED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskEvent.SUBMIT_FOR_REVIEW: TaskState.WAITING_REVIEW,
        TaskEvent.FAIL_RETRYABLE: TaskState.FAILED_RETRYABLE,
        TaskEvent.FAIL_TERMINAL: TaskState.FAILED_TERMINAL,
        TaskEvent.BLOCK: TaskState.BLOCKED,
        TaskEvent.CANCEL: TaskState.CANCEL_REQUESTED,
    },
    TaskState.WAITING_REVIEW: {
        TaskEvent.REVIEW_APPROVE: TaskState.SUCCEEDED,
        TaskEvent.REVIEW_REJECT: TaskState.PLANNED,
        TaskEvent.BLOCK: TaskState.BLOCKED,
        TaskEvent.CANCEL: TaskState.CANCELLED,
    },
    TaskState.FAILED_RETRYABLE: {TaskEvent.PLAN: TaskState.PLANNED, TaskEvent.BLOCK: TaskState.BLOCKED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.BLOCKED: {TaskEvent.RESUME: TaskState.VALIDATED, TaskEvent.CANCEL: TaskState.CANCELLED},
    TaskState.CANCEL_REQUESTED: {TaskEvent.CONFIRM_CANCEL: TaskState.CANCELLED, TaskEvent.BLOCK: TaskState.BLOCKED},
}


def transition_task(current: TaskState, event: TaskEvent, context: TransitionContext | None = None) -> TaskState:
    """Return a valid next state or reject deterministically; never mutates a task."""
    context = context or TransitionContext()
    if (
        current is TaskState.SUCCEEDED
        and event is TaskEvent.REVIEW_APPROVE
        and context.completion_operation_id
        and context.completion_idempotency_key
        and context.completion_operation_id == context.bound_operation_id
        and context.completion_idempotency_key == context.bound_idempotency_key
    ):
        return TaskState.SUCCEEDED
    next_state = _TRANSITIONS.get(current, {}).get(event)
    if next_state is None:
        raise TransitionRejected(f"{event.value} is invalid from {current.value}")
    if (
        current is TaskState.RUNNING
        and event is TaskEvent.FAIL_RETRYABLE
        and not (context.classified_transient_failure and context.attempt_budget_remaining and context.material_change_or_reassignment)
    ):
        raise TransitionRejected("retryable failure requires transient classification, budget, and a changed/reassigned attempt")
    if (
        current is TaskState.WAITING_REVIEW
        and event is TaskEvent.REVIEW_APPROVE
        and not (context.acceptance_met and context.verifier_receipt and context.evidence_receipts)
    ):
        raise TransitionRejected("success requires acceptance, verifier receipt, and evidence receipts")
    if current is TaskState.WAITING_REVIEW and event is TaskEvent.REVIEW_REJECT and not context.new_attempt_planned:
        raise TransitionRejected("review rejection requires a newly planned attempt")
    if (
        current is TaskState.BLOCKED
        and event is TaskEvent.RESUME
        and not (context.blocker_resolution_ref and context.references_revalidated)
    ):
        raise TransitionRejected("blocked task requires blocker resolution and reference revalidation")
    if (
        current is TaskState.CANCEL_REQUESTED
        and event is TaskEvent.CONFIRM_CANCEL
        and (context.effect_running or (not context.effect_reconciled and not context.cancellation_resolution_ref))
    ):
        raise TransitionRejected("cancellation requires effect reconciliation or a resolution receipt")
    if (
        context.attempt_generation is not None
        and context.result_generation is not None
        and context.result_generation != context.attempt_generation
        and event in {TaskEvent.REVIEW_APPROVE, TaskEvent.SUBMIT_FOR_REVIEW}
    ):
        raise TransitionRejected("stale generation result cannot advance task completion")
    return next_state


def result_matches_current_generation(current_generation: int, result_generation: int) -> bool:
    """Late provider results remain evidence but cannot complete a newer attempt."""
    return current_generation == result_generation


def apply_task_event(
    aggregate: TaskAggregate,
    *,
    event_id: str,
    event: TaskEvent,
    occurred_at: datetime,
    fingerprint: str,
    context: TransitionContext | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> TaskAggregate:
    """Append a logical transition record; exact event replay is idempotent."""
    if not event_id.strip() or len(fingerprint) != 64 or any(ch not in "0123456789abcdef" for ch in fingerprint.lower()):
        raise ValueError("event identity and SHA-256 fingerprint are required")
    if occurred_at.tzinfo is None:
        raise ValueError("event time must be timezone-aware")
    for record in aggregate.history:
        if record.event_id == event_id:
            if record.fingerprint == fingerprint and record.event is event:
                return aggregate
            raise EventIdentityConflict("event id was reused with different content")
    next_state = transition_task(aggregate.state, event, context)
    record = TaskTransitionRecord(event_id, aggregate.task_id, event, aggregate.state, next_state, occurred_at, fingerprint, evidence_refs)
    return TaskAggregate(aggregate.task_id, next_state, (*aggregate.history, record))
