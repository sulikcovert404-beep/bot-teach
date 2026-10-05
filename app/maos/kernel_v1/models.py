"""Immutable, provider-neutral Kernel V1 value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AgentRole(StrEnum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    ARCHITECTURE_REVIEWER = "architecture_reviewer"
    SECURITY_REVIEWER = "security_reviewer"


class Capability(StrEnum):
    REPO_READ = "repo_read"
    REPO_WRITE = "repo_write"
    TEST_RUN = "test_run"
    WEB_RESEARCH = "web_research"
    DB_READ_DISPOSABLE = "db_read_disposable"
    DB_MUTATE_DISPOSABLE = "db_mutate_disposable"
    DEPLOY_STAGING = "deploy_staging"
    DEPLOY_PRODUCTION = "deploy_production"


class AgentHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    RECOVERING = "recovering"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(StrEnum):
    ARCHITECTURE_REVIEW = "architecture_review"
    CODING = "coding"
    RESEARCH = "research"
    QA = "qa"


@dataclass(frozen=True, slots=True)
class TaskEnvelopeV1:
    schema_version: int
    task_id: str
    parent_task_id: str | None
    trace_id: str
    tenant_id: str
    principal_id: str
    purpose: str
    objective: str
    task_type: TaskType
    risk_class: RiskClass
    hard_constraints: tuple[str, ...]
    required_role: AgentRole
    provider_policy_ref: str
    capability_grant_refs: tuple[str, ...]
    allowed_resource_scope: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    context_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    output_schema_ref: str
    acceptance_criteria: tuple[str, ...]
    logical_attempt_budget: int
    cost_budget_ref: str
    token_budget_ref: str
    deadline: datetime
    attempt_no: int
    idempotency_scope: str
    created_by: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported task envelope schema version")
        required = (
            self.task_id,
            self.trace_id,
            self.tenant_id,
            self.principal_id,
            self.purpose,
            self.objective,
            self.provider_policy_ref,
            self.output_schema_ref,
            self.idempotency_scope,
            self.created_by,
        )
        if any(not value.strip() for value in required):
            raise ValueError("required task envelope identity/reference is empty")
        if self.logical_attempt_budget < 1 or self.attempt_no < 1:
            raise ValueError("attempt values must be positive")
        if self.attempt_no > self.logical_attempt_budget:
            raise ValueError("attempt number exceeds logical attempt budget")
        if self.deadline.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("task envelope times must be timezone-aware")
        for collection in (
            self.hard_constraints,
            self.capability_grant_refs,
            self.allowed_resource_scope,
            self.forbidden_actions,
            self.context_refs,
            self.evidence_refs,
            self.acceptance_criteria,
        ):
            if not isinstance(collection, tuple):
                raise TypeError("task envelope collections must be immutable tuples")
            if any(not value.strip() for value in collection):
                raise ValueError("task envelope collections cannot contain empty values")
        if self.parent_task_id is not None and not self.parent_task_id.strip():
            raise ValueError("parent task id cannot be empty")


@dataclass(frozen=True, slots=True)
class AgentRecord:
    logical_agent_id: str
    role: AgentRole
    capabilities: frozenset[Capability]
    input_schema_refs: tuple[str, ...]
    output_schema_refs: tuple[str, ...]
    policy_version: str
    provider_policy_ref: str
    health_state: AgentHealth
    health_evidence_ref: str
    updated_at: datetime
    version: int

    def __post_init__(self) -> None:
        if not all((self.logical_agent_id, self.policy_version, self.provider_policy_ref, self.health_evidence_ref)):
            raise ValueError("agent record references are required")
        if self.version < 1:
            raise ValueError("agent record version must be positive")
        if not isinstance(self.capabilities, frozenset) or not isinstance(self.input_schema_refs, tuple) or not isinstance(self.output_schema_refs, tuple):
            raise TypeError("agent capabilities and schema references must be immutable")
        if self.updated_at.tzinfo is None:
            raise ValueError("agent health timestamp must be timezone-aware")

    @property
    def dispatch_eligible(self) -> bool:
        return self.health_state is AgentHealth.HEALTHY
