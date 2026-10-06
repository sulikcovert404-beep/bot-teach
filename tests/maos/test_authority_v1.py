"""Contract tests for pure MAOS Authority Policy V1 values."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.maos.authority_v1 import (
    AUDIT_POLICY_V1,
    OPERATION_DOMAIN_V1,
    TENANT_POLICY_V1,
    AccountLifecycleEvent,
    AccountLifecycleHistory,
    AccountLifecycleState,
    ApprovalRecord,
    ApprovalState,
    ApproverGrant,
    ArchiveQualification,
    AuditAction,
    AuthorityAuditEvent,
    DelegationGrant,
    DelegationScope,
    EffectIntent,
    RiskPolicyActivation,
    RiskPolicyIdentity,
    TenantMultiplicityPolicy,
    TenantPolicyContractV1,
    append_lifecycle_event,
    authoritative_risk,
    bind_operation,
    critical_effects_enabled_v1,
    delegation_is_eligible,
    transition_approval,
)
from app.maos.kernel_v1.models import Capability, RiskClass

NOW = datetime(2026, 10, 6, 12, tzinfo=UTC)
DIGEST = "a" * 64


def lifecycle_event(
    event_id: str,
    from_state: AccountLifecycleState,
    to_state: AccountLifecycleState,
    *,
    at: datetime = NOW,
) -> AccountLifecycleEvent:
    return AccountLifecycleEvent(
        event_id=event_id,
        principal_id="principal-1",
        actor_principal_id="manager-1",
        from_state=from_state,
        to_state=to_state,
        reason_ref="reason:1",
        audit_event_ref=f"audit:{event_id}",
        occurred_at=at,
    )


def high_approval(*, risk: RiskClass = RiskClass.HIGH) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="approval-1",
        requester_principal_id="requester-1",
        operation_digest=DIGEST,
        risk_class=risk,
        state=ApprovalState.REQUESTED,
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def approver_grant(**changes: object) -> ApproverGrant:
    values: dict[str, object] = {
        "grant_id": "grant-1",
        "approver_principal_id": "approver-1",
        "issuer_principal_id": "manager-1",
        "risk_tiers": frozenset({RiskClass.HIGH}),
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
        "grant_ref": "grant-ref:1",
    }
    values.update(changes)
    return ApproverGrant(**values)  # type: ignore[arg-type]


def test_account_status_defaults_unreconciled_and_lifecycle_is_append_only() -> None:
    history = AccountLifecycleHistory("principal-1")
    assert history.current_state is AccountLifecycleState.UNRECONCILED
    assert not history.maos_effect_eligible

    activated = append_lifecycle_event(
        history,
        lifecycle_event("event-1", AccountLifecycleState.UNRECONCILED, AccountLifecycleState.ACTIVE),
    )
    assert activated.current_state is AccountLifecycleState.ACTIVE
    assert activated.maos_effect_eligible
    assert len(history.events) == 0
    assert append_lifecycle_event(activated, activated.events[0]) is activated

    suspended = append_lifecycle_event(
        activated,
        lifecycle_event(
            "event-2",
            AccountLifecycleState.ACTIVE,
            AccountLifecycleState.SUSPENDED,
            at=NOW + timedelta(seconds=1),
        ),
    )
    assert suspended.current_state is AccountLifecycleState.SUSPENDED
    assert not suspended.maos_effect_eligible


def test_account_lifecycle_rejects_gaps_replay_conflicts_and_disabled_reactivation() -> None:
    history = append_lifecycle_event(
        AccountLifecycleHistory("principal-1"),
        lifecycle_event("event-1", AccountLifecycleState.UNRECONCILED, AccountLifecycleState.DISABLED),
    )
    with pytest.raises(ValueError, match="does not continue"):
        append_lifecycle_event(
            history,
            lifecycle_event(
                "event-2", AccountLifecycleState.ACTIVE, AccountLifecycleState.SUSPENDED,
                at=NOW + timedelta(seconds=1),
            ),
        )
    with pytest.raises(ValueError, match="invalid account lifecycle"):
        lifecycle_event("event-3", AccountLifecycleState.DISABLED, AccountLifecycleState.ACTIVE)


def test_account_lifecycle_history_rejects_unanchored_active_cycle() -> None:
    partial_history = (
        lifecycle_event("event-1", AccountLifecycleState.ACTIVE, AccountLifecycleState.SUSPENDED),
        lifecycle_event(
            "event-2",
            AccountLifecycleState.SUSPENDED,
            AccountLifecycleState.ACTIVE,
            at=NOW + timedelta(seconds=1),
        ),
    )

    with pytest.raises(ValueError, match="UNRECONCILED anchor"):
        AccountLifecycleHistory("principal-1", partial_history)


def test_account_lifecycle_history_accepts_explicit_unreconciled_anchor() -> None:
    history = AccountLifecycleHistory(
        "principal-1",
        (
            lifecycle_event(
                "event-1", AccountLifecycleState.UNRECONCILED, AccountLifecycleState.ACTIVE
            ),
        ),
    )

    assert history.current_state is AccountLifecycleState.ACTIVE
    assert history.maos_effect_eligible


def test_tenant_contract_is_exactly_one_canonical_membership_only() -> None:
    assert TENANT_POLICY_V1.policy is TenantMultiplicityPolicy.EXACTLY_ONE_ACTIVE_CANONICAL
    assert TENANT_POLICY_V1.required_active_memberships == 1
    assert TENANT_POLICY_V1.multi_tenant_selection_enabled is False
    with pytest.raises(ValueError, match="exact-one"):
        TenantPolicyContractV1(required_active_memberships=2)


def test_high_approval_requires_distinct_requester_and_current_grant() -> None:
    record = high_approval()
    approved = transition_approval(
        record,
        ApprovalState.APPROVED,
        actor_principal_id="approver-1",
        event_ref="approval-event:1",
        occurred_at=NOW,
        approver_grant=approver_grant(),
    )
    assert approved.state is ApprovalState.APPROVED
    assert approved.approver_grant_ref == "grant-ref:1"
    assert approved.operation_digest == DIGEST

    consumed = transition_approval(
        approved,
        ApprovalState.CONSUMED,
        actor_principal_id="approver-1",
        event_ref="approval-event:2",
        occurred_at=NOW + timedelta(seconds=1),
    )
    assert consumed.state is ApprovalState.CONSUMED
    with pytest.raises(ValueError, match="terminal-state replay"):
        transition_approval(
            consumed,
            ApprovalState.CONSUMED,
            actor_principal_id="approver-1",
            event_ref="approval-event:3",
            occurred_at=NOW + timedelta(seconds=2),
        )


def test_approval_denies_self_approval_missing_stale_revoked_and_critical() -> None:
    with pytest.raises(ValueError, match="requester cannot"):
        transition_approval(
            high_approval(), ApprovalState.APPROVED,
            actor_principal_id="requester-1", event_ref="evt:1", occurred_at=NOW,
            approver_grant=approver_grant(approver_principal_id="requester-1"),
        )
    with pytest.raises(ValueError, match="ApproverGrant"):
        transition_approval(
            high_approval(), ApprovalState.APPROVED,
            actor_principal_id="approver-1", event_ref="evt:2", occurred_at=NOW,
        )
    revoked_grant = approver_grant(revocation_ref="revocation:1")
    with pytest.raises(ValueError, match="ApproverGrant"):
        transition_approval(
            high_approval(), ApprovalState.APPROVED,
            actor_principal_id="approver-1", event_ref="evt:3", occurred_at=NOW,
            approver_grant=revoked_grant,
        )
    expired_grant = approver_grant(expires_at=NOW)
    with pytest.raises(ValueError, match="ApproverGrant"):
        transition_approval(
            high_approval(), ApprovalState.APPROVED,
            actor_principal_id="approver-1", event_ref="evt:4", occurred_at=NOW,
            approver_grant=expired_grant,
        )
    with pytest.raises(ValueError, match="CRITICAL"):
        transition_approval(
            high_approval(risk=RiskClass.CRITICAL), ApprovalState.REJECTED,
            actor_principal_id="approver-1", event_ref="evt:5", occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="CRITICAL"):
        approver_grant(risk_tiers=frozenset({RiskClass.CRITICAL}))
    assert critical_effects_enabled_v1() is False


def test_approval_expiry_and_terminal_states_fail_closed() -> None:
    record = high_approval()
    expired = transition_approval(
        record,
        ApprovalState.EXPIRED,
        actor_principal_id="system:expiry",
        event_ref="expiry:1",
        occurred_at=record.expires_at,
    )
    assert expired.state is ApprovalState.EXPIRED
    with pytest.raises(ValueError, match="cannot expire before"):
        transition_approval(
            record, ApprovalState.EXPIRED, actor_principal_id="system:expiry",
            event_ref="expiry:2", occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="expired"):
        transition_approval(
            record, ApprovalState.REJECTED, actor_principal_id="approver-1",
            event_ref="reject:1", occurred_at=record.expires_at,
        )


def test_risk_policy_identity_and_activation_require_release_and_manager_refs() -> None:
    identity = RiskPolicyIdentity("maos-risk", "v1", DIGEST)
    activation = RiskPolicyActivation(identity, "release:1", "manager-approval:1", NOW)
    assert activation.identity == identity
    with pytest.raises(ValueError, match="SHA-256"):
        RiskPolicyIdentity("maos-risk", "v1", "missing")
    with pytest.raises(ValueError, match="lowercase"):
        RiskPolicyIdentity("maos-risk", "v1", "A" * 64)
    with pytest.raises(ValueError, match="cannot be empty"):
        RiskPolicyActivation(identity, "release:1", "", NOW)


def test_agent_risk_can_only_raise_and_missing_policy_is_critical() -> None:
    assert authoritative_risk(RiskClass.HIGH, (RiskClass.LOW,)) is RiskClass.HIGH
    assert authoritative_risk(RiskClass.LOW, (RiskClass.CRITICAL,)) is RiskClass.CRITICAL
    assert authoritative_risk(None) is RiskClass.CRITICAL
    with pytest.raises(TypeError, match="immutable tuple"):
        authoritative_risk(RiskClass.LOW, [RiskClass.HIGH])  # type: ignore[arg-type]


def test_audit_v1_forbids_delete_and_purge_and_gates_archive_qualification() -> None:
    assert AUDIT_POLICY_V1.permits(AuditAction.APPEND)
    assert not AUDIT_POLICY_V1.permits(AuditAction.ARCHIVE)
    assert not AUDIT_POLICY_V1.permits(AuditAction.ARCHIVE, ArchiveQualification(True, False, True))
    assert AUDIT_POLICY_V1.permits(AuditAction.ARCHIVE, ArchiveQualification(True, True, True))
    assert not AUDIT_POLICY_V1.permits(AuditAction.DELETE)
    assert not AUDIT_POLICY_V1.permits(AuditAction.PURGE)
    with pytest.raises(ValueError, match="disabled"):
        replace(AUDIT_POLICY_V1, purge_enabled=True)


def test_audit_and_effect_intent_bind_policy_and_operation_without_payload() -> None:
    identity = RiskPolicyIdentity("risk-v1", "1", DIGEST)
    event = AuthorityAuditEvent("event:1", "principal:1", "approve", "resource:1", DIGEST, identity, NOW)
    intent = EffectIntent("intent:1", DIGEST, "decision:1", event.event_id, Capability.REPO_READ, RiskClass.HIGH)
    assert event.policy_identity is identity
    assert intent.operation_digest == event.operation_digest
    with pytest.raises(ValueError, match="CRITICAL"):
        EffectIntent("intent:2", DIGEST, "decision:2", event.event_id, Capability.REPO_WRITE, RiskClass.CRITICAL)


def test_delegation_is_bounded_expiring_revocable_and_non_transitive() -> None:
    parent = DelegationScope(frozenset({Capability.REPO_READ, Capability.TEST_RUN}), frozenset({"repo:a", "repo:b"}), RiskClass.HIGH)
    child = DelegationScope(frozenset({Capability.REPO_READ}), frozenset({"repo:a"}), RiskClass.MEDIUM)
    grant = DelegationGrant("delegation:1", "parent:1", "issuer:1", "delegate:1", child, NOW, NOW + timedelta(minutes=5))
    assert delegation_is_eligible(grant, parent_scope=parent, requested_scope=child, at=NOW)
    assert not delegation_is_eligible(grant, parent_scope=None, requested_scope=child, at=NOW)
    assert not delegation_is_eligible(grant, parent_scope=parent, requested_scope=child, at=grant.expires_at)
    assert not delegation_is_eligible(
        replace(grant, revocation_ref="revoke:1"), parent_scope=parent, requested_scope=child, at=NOW
    )
    broader = DelegationScope(frozenset({Capability.REPO_WRITE}), frozenset({"repo:a"}), RiskClass.HIGH)
    assert not delegation_is_eligible(grant, parent_scope=parent, requested_scope=broader, at=NOW)
    with pytest.raises(ValueError, match="non-transitive"):
        replace(grant, transitive=True)


def test_operation_binding_is_stable_domain_separated_and_secret_aware() -> None:
    first = bind_operation(
        principal_id="p1", tenant_id="t1", action="update", resource_ref="lesson:1",
        parameters={"z": 2, "a": ["café", True]},
    )
    second = bind_operation(
        principal_id="p1", tenant_id="t1", action="update", resource_ref="lesson:1",
        parameters={"a": ["cafe\u0301", True], "z": 2},
    )
    assert first == second
    assert first.domain == OPERATION_DOMAIN_V1 == "maos.operation.v1"
    assert len(first.digest) == 64
    assert "secret-value" not in first.canonical_json
    with pytest.raises(ValueError, match="secret-bearing"):
        bind_operation(
            principal_id="p1", tenant_id="t1", action="update", resource_ref="lesson:1",
            parameters={"access_token": "secret-value"},
        )
    with pytest.raises(ValueError, match="credential-like"):
        bind_operation(
            principal_id="p1", tenant_id="t1", action="call", resource_ref="provider",
            parameters={"header": "Bearer abc123"},
        )
    with pytest.raises(ValueError, match="credential-like"):
        bind_operation(
            principal_id="Bearer abc123", tenant_id="t1", action="call", resource_ref="provider"
        )
    with pytest.raises(TypeError, match="floating-point"):
        bind_operation(
            principal_id="p1", tenant_id="t1", action="update", resource_ref="lesson:1",
            parameters={"score": 0.5},
        )
    with pytest.raises(TypeError, match="unsupported canonical"):
        bind_operation(
            principal_id="p1", tenant_id="t1", action="update", resource_ref="lesson:1",
            parameters={"unsupported": NOW},
        )
    with pytest.raises(ValueError, match="does not match"):
        replace(first, digest="b" * 64)


def test_delegation_scope_and_archive_qualification_are_immutable_contracts() -> None:
    with pytest.raises(ValueError, match="exact references"):
        DelegationScope(frozenset({Capability.REPO_READ}), frozenset({"*"}), RiskClass.LOW)
