from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.maos.kernel_v1 import (
    AgentHealth,
    AgentRecord,
    AgentRole,
    ArtifactReference,
    AuthorizationRequest,
    Capability,
    CapabilityGrant,
    DecisionAuthority,
    DecisionRecord,
    EnvelopeValidationContext,
    EvidenceEntry,
    EvidenceHistory,
    FailureClass,
    IdempotencyKey,
    OperationId,
    RetryBudget,
    ReviewOutcome,
    ReviewRecord,
    RiskClass,
    TaskAggregate,
    TaskEnvelopeV1,
    TaskEvent,
    TaskState,
    TaskType,
    TenantAuthorizationContext,
    TransitionContext,
    TransitionRejected,
    append_evidence,
    apply_task_event,
    assess_risk,
    decide_retry,
    evaluate_capability_grant,
    result_matches_current_generation,
    transition_agent_health,
    transition_task,
    validate_task_envelope,
)
from app.maos.kernel_v1.agents import AgentHealthTransitionRejected
from app.maos.kernel_v1.lifecycle import EventIdentityConflict

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)
HASH = "a" * 64


def envelope(**changes: object) -> TaskEnvelopeV1:
    values: dict[str, object] = {
        "schema_version": 1,
        "task_id": "task-1",
        "parent_task_id": None,
        "trace_id": "trace-1",
        "tenant_id": "tenant-selector",
        "principal_id": "principal-1",
        "purpose": "lesson_review",
        "objective": "review content",
        "task_type": TaskType.QA,
        "risk_class": RiskClass.LOW,
        "hard_constraints": ("no_external_io",),
        "required_role": AgentRole.VERIFIER,
        "provider_policy_ref": "gateway-policy-v1",
        "capability_grant_refs": (),
        "allowed_resource_scope": ("artifact:1",),
        "forbidden_actions": ("deploy",),
        "context_refs": ("context:1",),
        "evidence_refs": (),
        "output_schema_ref": "schema:review-v1",
        "acceptance_criteria": ("citations verified",),
        "logical_attempt_budget": 2,
        "cost_budget_ref": "cost-policy-v1",
        "token_budget_ref": "token-policy-v1",
        "deadline": NOW + timedelta(minutes=5),
        "attempt_no": 1,
        "idempotency_scope": "task-1",
        "created_by": "commander",
        "expires_at": NOW + timedelta(minutes=10),
    }
    values.update(changes)
    return TaskEnvelopeV1(**values)  # type: ignore[arg-type]


def grant() -> CapabilityGrant:
    return CapabilityGrant(
        grant_id="grant-1",
        task_id="task-1",
        principal_id="principal-1",
        tenant_id="tenant-1",
        capability=Capability.REPO_READ,
        resource_scope=frozenset({"artifact:1"}),
        risk_class=RiskClass.LOW,
        issuer="policy-engine",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=1),
        constraints=frozenset({"read_only"}),
        policy_version="policy-1",
    )


def auth_request(**changes: object) -> AuthorizationRequest:
    values: dict[str, object] = {
        "task_id": "task-1",
        "principal_id": "principal-1",
        "capability": Capability.REPO_READ,
        "resource_id": "artifact:1",
        "risk_class": RiskClass.LOW,
        "policy_version": "policy-1",
        "requested_at": NOW,
        "tenant_context": TenantAuthorizationContext("principal-1", "tenant-1", "review", "authz-1", "policy-1"),
        "approved_grant_issuers": frozenset({"policy-engine"}),
    }
    values.update(changes)
    return AuthorizationRequest(**values)  # type: ignore[arg-type]


def agent(health: AgentHealth = AgentHealth.HEALTHY) -> AgentRecord:
    return AgentRecord(
        logical_agent_id="reviewer-a",
        role=AgentRole.ARCHITECTURE_REVIEWER,
        capabilities=frozenset({Capability.REPO_READ}),
        input_schema_refs=("task-v1",),
        output_schema_refs=("review-v1",),
        policy_version="policy-1",
        provider_policy_ref="gateway-policy-v1",
        health_state=health,
        health_evidence_ref="health-evidence-1",
        updated_at=NOW,
        version=1,
    )


def test_task_envelope_is_versioned_scoped_and_provider_neutral() -> None:
    task = envelope()
    assert task.schema_version == 1
    assert task.tenant_id == "tenant-selector"  # selector only; resolver port owns authority
    assert task.provider_policy_ref == "gateway-policy-v1"
    assert task.required_role is AgentRole.VERIFIER
    with pytest.raises(ValueError, match="schema version"):
        envelope(schema_version=2)
    with pytest.raises(ValueError, match="attempt number"):
        envelope(attempt_no=3)
    with pytest.raises(ValueError, match="timezone-aware"):
        envelope(deadline=NOW.replace(tzinfo=None), expires_at=NOW.replace(tzinfo=None))


def test_envelope_validation_fails_closed_on_tenant_grant_and_time_boundaries() -> None:
    task = envelope(capability_grant_refs=("grant-1",))
    tenant = TenantAuthorizationContext("principal-1", "tenant-selector", "lesson_review", "authz:1", "policy:1")
    passed = validate_task_envelope(task, EnvelopeValidationContext(NOW, tenant, frozenset({"grant-1"})))
    assert passed.valid
    denied = validate_task_envelope(task, EnvelopeValidationContext(NOW, None, frozenset()))
    assert not denied.valid
    assert set(denied.errors) == {"tenant_authority_unresolved", "capability_grant_reference_missing"}
    mismatch = TenantAuthorizationContext("principal-other", "tenant-selector", "lesson_review", "authz:2", "policy:1")
    assert "tenant_authority_scope_mismatch" in validate_task_envelope(task, EnvelopeValidationContext(NOW, mismatch, frozenset({"grant-1"}))).errors
    assert "task_deadline_elapsed" in validate_task_envelope(task, EnvelopeValidationContext(task.deadline, tenant, frozenset({"grant-1"}))).errors


def test_task_lifecycle_requires_validation_review_and_evidence_before_success() -> None:
    state = TaskState.CREATED
    for event, expected in (
        (TaskEvent.VALIDATE, TaskState.VALIDATED),
        (TaskEvent.PLAN, TaskState.PLANNED),
        (TaskEvent.DISPATCH, TaskState.DISPATCHED),
        (TaskEvent.START, TaskState.RUNNING),
        (TaskEvent.SUBMIT_FOR_REVIEW, TaskState.WAITING_REVIEW),
    ):
        state = transition_task(state, event)
        assert state is expected
    with pytest.raises(TransitionRejected, match="success requires"):
        transition_task(state, TaskEvent.REVIEW_APPROVE)
    assert transition_task(
        state,
        TaskEvent.REVIEW_APPROVE,
        TransitionContext(acceptance_met=True, verifier_receipt="review:1", evidence_receipts=("evidence:1",)),
    ) is TaskState.SUCCEEDED
    with pytest.raises(TransitionRejected, match="invalid"):
        transition_task(TaskState.SUCCEEDED, TaskEvent.CANCEL)


def test_review_rejection_returns_to_planned_only_with_new_attempt() -> None:
    with pytest.raises(TransitionRejected, match="newly planned"):
        transition_task(TaskState.WAITING_REVIEW, TaskEvent.REVIEW_REJECT)
    assert transition_task(
        TaskState.WAITING_REVIEW,
        TaskEvent.REVIEW_REJECT,
        TransitionContext(new_attempt_planned=True),
    ) is TaskState.PLANNED


def test_retryable_transition_requires_classification_budget_and_changed_attempt() -> None:
    with pytest.raises(TransitionRejected, match="transient classification"):
        transition_task(TaskState.RUNNING, TaskEvent.FAIL_RETRYABLE)
    context = TransitionContext(
        classified_transient_failure=True,
        attempt_budget_remaining=True,
        material_change_or_reassignment=True,
    )
    assert transition_task(TaskState.RUNNING, TaskEvent.FAIL_RETRYABLE, context) is TaskState.FAILED_RETRYABLE
    assert transition_task(TaskState.FAILED_RETRYABLE, TaskEvent.PLAN) is TaskState.PLANNED


def test_block_resume_requires_resolution_and_revalidation() -> None:
    with pytest.raises(TransitionRejected, match="blocker resolution"):
        transition_task(TaskState.BLOCKED, TaskEvent.RESUME)
    context = TransitionContext(blocker_resolution_ref="decision:1", references_revalidated=True)
    assert transition_task(TaskState.BLOCKED, TaskEvent.RESUME, context) is TaskState.VALIDATED


def test_running_cancel_is_only_a_request_until_effect_reconciles() -> None:
    assert transition_task(TaskState.RUNNING, TaskEvent.CANCEL) is TaskState.CANCEL_REQUESTED
    with pytest.raises(TransitionRejected, match="effect reconciliation"):
        transition_task(TaskState.CANCEL_REQUESTED, TaskEvent.CONFIRM_CANCEL)
    context = TransitionContext(effect_reconciled=True, cancellation_resolution_ref="operation:1")
    assert transition_task(TaskState.CANCEL_REQUESTED, TaskEvent.CONFIRM_CANCEL, context) is TaskState.CANCELLED


def test_late_attempt_result_is_stale_and_cannot_advance_lifecycle() -> None:
    assert not result_matches_current_generation(2, 1)
    assert result_matches_current_generation(2, 2)
    with pytest.raises(TransitionRejected, match="stale generation"):
        transition_task(
            TaskState.WAITING_REVIEW,
            TaskEvent.REVIEW_APPROVE,
            TransitionContext(
                acceptance_met=True,
                verifier_receipt="review:1",
                evidence_receipts=("evidence:1",),
                attempt_generation=2,
                result_generation=1,
            ),
        )


def test_duplicate_completion_is_idempotent_only_for_same_operation_identity() -> None:
    assert transition_task(
        TaskState.SUCCEEDED,
        TaskEvent.REVIEW_APPROVE,
        TransitionContext(
            completion_operation_id="op-1",
            completion_idempotency_key="key-1",
            bound_operation_id="op-1",
            bound_idempotency_key="key-1",
        ),
    ) is TaskState.SUCCEEDED
    with pytest.raises(TransitionRejected):
        transition_task(TaskState.SUCCEEDED, TaskEvent.REVIEW_APPROVE, TransitionContext(completion_operation_id="op-2"))
    assert OperationId("op-1").value == "op-1"
    assert IdempotencyKey("key-1").value == "key-1"


def test_logical_event_history_appends_and_exact_replay_is_idempotent() -> None:
    aggregate = TaskAggregate("task-1", TaskState.CREATED)
    changed = apply_task_event(aggregate, event_id="event-1", event=TaskEvent.VALIDATE, occurred_at=NOW, fingerprint=HASH)
    assert changed.state is TaskState.VALIDATED
    assert len(changed.history) == 1
    assert apply_task_event(changed, event_id="event-1", event=TaskEvent.VALIDATE, occurred_at=NOW, fingerprint=HASH) is changed
    with pytest.raises(EventIdentityConflict):
        apply_task_event(changed, event_id="event-1", event=TaskEvent.CANCEL, occurred_at=NOW, fingerprint="b" * 64)


def test_agent_role_and_provider_policy_are_separate_and_health_gates_dispatch() -> None:
    record = agent(AgentHealth.DEGRADED)
    assert record.logical_agent_id != record.provider_policy_ref
    assert not record.dispatch_eligible
    with pytest.raises(AgentHealthTransitionRejected, match="cannot self-update"):
        transition_agent_health(record, AgentHealth.RECOVERING, evidence_ref="probe:1", policy_version="p2", occurred_at=NOW, authorized_by_health_policy=False)
    recovering = transition_agent_health(record, AgentHealth.RECOVERING, evidence_ref="probe:1", policy_version="p2", occurred_at=NOW + timedelta(seconds=1), authorized_by_health_policy=True)
    assert not recovering.dispatch_eligible  # recovery probing is not ordinary dispatch eligibility
    assert recovering.version == record.version + 1
    healthy = transition_agent_health(recovering, AgentHealth.HEALTHY, evidence_ref="qualified-probe:1", policy_version="p2", occurred_at=NOW + timedelta(seconds=2), authorized_by_health_policy=True)
    assert healthy.dispatch_eligible
    quarantined = agent(AgentHealth.QUARANTINED)
    with pytest.raises(AgentHealthTransitionRejected, match="integrity clearance"):
        transition_agent_health(quarantined, AgentHealth.RECOVERING, evidence_ref="probe:1", policy_version="p2", occurred_at=NOW + timedelta(seconds=1), authorized_by_health_policy=True)


def test_authority_denies_missing_scope_issuer_forbidden_capability_and_unapproved_decision() -> None:
    assert evaluate_capability_grant(grant(), auth_request()).allowed
    assert not evaluate_capability_grant(None, auth_request()).allowed
    assert not evaluate_capability_grant(grant(), auth_request(tenant_context=None)).allowed
    assert not evaluate_capability_grant(grant(), auth_request(approved_grant_issuers=frozenset())).allowed
    assert not evaluate_capability_grant(grant(), auth_request(forbidden_actions=frozenset({Capability.REPO_READ}))).allowed
    assert not evaluate_capability_grant(grant(), auth_request(human_decision_required=True)).allowed
    assert not evaluate_capability_grant(grant(), auth_request(resource_id="artifact:other")).allowed
    assert not evaluate_capability_grant(grant(), auth_request(tenant_context=TenantAuthorizationContext("principal-1", "tenant-other", "review", "authz-1", "policy-1"))).allowed


def test_expired_or_revoked_grant_and_agent_risk_cannot_reduce_authority() -> None:
    expired = grant()
    expired = replace(expired, expires_at=NOW)
    assert not evaluate_capability_grant(expired, auth_request()).allowed
    revoked = replace(grant(), revocation_ref="revoke:1")
    assert not evaluate_capability_grant(revoked, auth_request()).allowed
    result = assess_risk(RiskClass.HIGH, RiskClass.LOW, decision_gate_approved=False, rationale_ref="policy-evidence:1")
    assert result.effective_risk is RiskClass.HIGH
    assert result.decision_gate_required and not result.authorized_to_proceed
    missing_policy = assess_risk(None, RiskClass.LOW, decision_gate_approved=True, rationale_ref="")
    assert missing_policy.effective_risk is RiskClass.CRITICAL and not missing_policy.authorized_to_proceed


def test_retry_budgets_separate_provider_calls_from_task_attempts_and_fail_closed() -> None:
    budget = RetryBudget(1, 2, 1, 2, 1, 3, 1, 3)
    provider_retry = decide_retry(FailureClass.PROVIDER_TRANSIENT, budget)
    assert provider_retry.retry_provider_call and not provider_retry.retry_task_attempt
    assert not decide_retry(FailureClass.AUTHORIZATION, budget).retry_provider_call
    assert not decide_retry(FailureClass.POLICY_VIOLATION, budget).retry_task_attempt
    assert decide_retry(FailureClass.AGENT_SCHEMA, budget).retry_provider_call
    assert decide_retry(FailureClass.DEPENDENCY_UNAVAILABLE, budget).blocked
    assert decide_retry(FailureClass.TIMEOUT, budget).blocked
    reconciled = decide_retry(FailureClass.TIMEOUT, budget, material_change_or_reassignment=True, effect_operation_reconciled=True)
    assert reconciled.retry_task_attempt
    exhausted = RetryBudget(2, 2, 2, 2, 3, 3, 1, 1)
    assert decide_retry(FailureClass.PROVIDER_TRANSIENT, exhausted).blocked
    assert decide_retry(FailureClass.TOOL, budget, material_change_or_reassignment=True).blocked


def evidence(evidence_id: str, supersedes: str | None = None) -> EvidenceEntry:
    return EvidenceEntry(
        evidence_id=evidence_id,
        task_id="task-1",
        trace_id="trace-1",
        producer_id="verifier-1",
        producer_principal_id="principal-1",
        logical_role="verifier",
        provider_ref=None,
        source_type="test",
        source_locator_ref="source:1",
        content_hash=HASH,
        captured_at=NOW,
        observed_at=NOW,
        method="unit_test",
        schema_version="evidence-v1",
        limitations=("synthetic",),
        freshness_ref=None,
        tenant_id="tenant-1",
        artifact_ref="artifact:1",
        redaction_status="non_sensitive",
        supersedes_evidence_id=supersedes,
    )


def test_evidence_history_is_append_only_logically_and_supersession_is_explicit() -> None:
    first = evidence("e1")
    history = append_evidence(EvidenceHistory(), first)
    with pytest.raises(ValueError, match="cannot be overwritten"):
        append_evidence(history, first)
    with pytest.raises(ValueError, match="must already exist"):
        append_evidence(history, evidence("e3", "missing"))
    second = evidence("e2", "e1")
    extended = append_evidence(history, second)
    assert len(history.entries) == 1
    assert len(extended.entries) == 2
    assert extended.entries[1].supersedes_evidence_id == "e1"


def test_artifact_review_and_decision_records_retain_provenance_and_authority() -> None:
    artifact = ArtifactReference("artifact-1", "task-1", "executor-1", HASH, "artifact-v1", NOW, "tenant-1")
    assert artifact.content_hash == HASH
    with pytest.raises(ValueError, match="distinct logical instances"):
        ReviewRecord("review-1", "task-1", "principal-1", "instance-a", "instance-a", "verifier", ReviewOutcome.APPROVE, ("criteria:1",), ("evidence:1",), "provenance:1", NOW)
    review = ReviewRecord("review-1", "task-1", "principal-1", "instance-reviewer", "instance-executor", "verifier", ReviewOutcome.APPROVE, ("criteria:1",), ("evidence:1",), "provenance:1", NOW)
    assert review.reviewer_instance_id != review.author_instance_id
    with pytest.raises(ValueError, match="Commander gate"):
        DecisionRecord("decision-1", DecisionAuthority.POLICY_ENGINE, "task-1", "action:1", "rationale:1", ("evidence:1",), RiskClass.HIGH, False, NOW, "policy-1")
    decision = DecisionRecord("decision-1", DecisionAuthority.COMMANDER, "task-1", "action:1", "rationale:1", ("evidence:1",), RiskClass.HIGH, False, NOW, "policy-1", "gate:1")
    assert decision.authority is DecisionAuthority.COMMANDER
