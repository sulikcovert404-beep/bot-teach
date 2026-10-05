"""Bounded, classified retry decisions with separate task/provider budgets."""

from dataclasses import dataclass
from enum import StrEnum


class FailureClass(StrEnum):
    PROVIDER_TRANSIENT = "provider_transient"
    PROVIDER_TERMINAL = "provider_terminal"
    AGENT_SCHEMA = "agent_schema_failure"
    TOOL = "tool_failure"
    AUTHORIZATION = "authorization_failure"
    POLICY_VIOLATION = "policy_violation"
    TIMEOUT = "timeout"
    STALE_GENERATION = "stale_generation"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    HUMAN_DECISION_BLOCKED = "human_decision_blocked"


@dataclass(frozen=True, slots=True)
class RetryBudget:
    task_attempts_used: int
    task_attempts_max: int
    provider_calls_used: int
    provider_calls_max: int
    total_calls_used: int
    total_calls_max: int
    schema_corrections_used: int = 0
    schema_corrections_max: int = 0

    def __post_init__(self) -> None:
        values = (
            self.task_attempts_used,
            self.task_attempts_max,
            self.provider_calls_used,
            self.provider_calls_max,
            self.total_calls_used,
            self.total_calls_max,
            self.schema_corrections_used,
            self.schema_corrections_max,
        )
        if any(value < 0 for value in values):
            raise ValueError("retry budget values cannot be negative")
        if self.task_attempts_used > self.task_attempts_max or self.provider_calls_used > self.provider_calls_max or self.total_calls_used > self.total_calls_max or self.schema_corrections_used > self.schema_corrections_max:
            raise ValueError("retry budget usage cannot exceed its ceiling")


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry_provider_call: bool
    retry_task_attempt: bool
    blocked: bool
    reason: str


def decide_retry(
    failure: FailureClass,
    budget: RetryBudget,
    *,
    material_change_or_reassignment: bool = False,
    effect_operation_reconciled: bool = False,
) -> RetryDecision:
    """Compute one bounded retry disposition; never replays uncertain tool effects."""
    if failure in {FailureClass.AUTHORIZATION, FailureClass.POLICY_VIOLATION, FailureClass.PROVIDER_TERMINAL, FailureClass.STALE_GENERATION}:
        return RetryDecision(False, False, False, "terminal_or_authority_failure")
    if failure in {FailureClass.DEPENDENCY_UNAVAILABLE, FailureClass.HUMAN_DECISION_BLOCKED}:
        return RetryDecision(False, False, True, "external_decision_or_dependency_required")
    if failure is FailureClass.AGENT_SCHEMA:
        can_correct = (
            budget.schema_corrections_used < budget.schema_corrections_max
            and budget.total_calls_used < budget.total_calls_max
        )
        return RetryDecision(can_correct, False, not can_correct, "bounded_schema_correction" if can_correct else "schema_correction_budget_exhausted")
    if failure is FailureClass.PROVIDER_TRANSIENT:
        can_retry = (
            budget.provider_calls_used < budget.provider_calls_max
            and budget.total_calls_used < budget.total_calls_max
        )
        return RetryDecision(can_retry, False, not can_retry, "bounded_provider_retry" if can_retry else "provider_call_budget_exhausted")
    if failure is FailureClass.TIMEOUT:
        if not effect_operation_reconciled:
            return RetryDecision(False, False, True, "timeout_result_uncertain_reconcile_by_operation_identity")
        can_retry = (
            budget.task_attempts_used < budget.task_attempts_max
            and budget.total_calls_used < budget.total_calls_max
            and material_change_or_reassignment
        )
        return RetryDecision(False, can_retry, not can_retry, "reconciled_changed_attempt" if can_retry else "bounded_retry_not_qualified")
    if failure is FailureClass.TOOL:
        if not effect_operation_reconciled:
            return RetryDecision(False, False, True, "tool_result_uncertain_reconcile_by_operation_identity")
        can_retry = (
            budget.task_attempts_used < budget.task_attempts_max
            and budget.total_calls_used < budget.total_calls_max
            and material_change_or_reassignment
        )
        return RetryDecision(False, can_retry, not can_retry, "reconciled_changed_attempt" if can_retry else "bounded_retry_not_qualified")
    return RetryDecision(False, False, True, "unknown_failure_class")
