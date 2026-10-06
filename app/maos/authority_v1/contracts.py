"""Pure, fail-closed authority-policy value contracts for MAOS V1.

These values describe policy and transitions. They do not issue authority,
resolve identities, persist state, or perform external effects.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from app.maos.kernel_v1.models import Capability, RiskClass


class AccountLifecycleState(StrEnum):
    UNRECONCILED = "unreconciled"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class AccountLifecycleEvent:
    event_id: str
    principal_id: str
    actor_principal_id: str
    from_state: AccountLifecycleState
    to_state: AccountLifecycleState
    reason_ref: str
    audit_event_ref: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        _require_texts(
            event_id=self.event_id,
            principal_id=self.principal_id,
            actor_principal_id=self.actor_principal_id,
            reason_ref=self.reason_ref,
            audit_event_ref=self.audit_event_ref,
        )
        _require_aware(self.occurred_at, "lifecycle event time")
        if self.from_state is self.to_state:
            raise ValueError("lifecycle event must change account state")
        if self.to_state not in _ACCOUNT_TRANSITIONS.get(self.from_state, frozenset()):
            raise ValueError("invalid account lifecycle transition")


_ACCOUNT_TRANSITIONS: dict[AccountLifecycleState, frozenset[AccountLifecycleState]] = {
    AccountLifecycleState.UNRECONCILED: frozenset(
        {AccountLifecycleState.ACTIVE, AccountLifecycleState.SUSPENDED, AccountLifecycleState.DISABLED}
    ),
    AccountLifecycleState.ACTIVE: frozenset(
        {AccountLifecycleState.SUSPENDED, AccountLifecycleState.DISABLED}
    ),
    AccountLifecycleState.SUSPENDED: frozenset(
        {AccountLifecycleState.ACTIVE, AccountLifecycleState.DISABLED}
    ),
    AccountLifecycleState.DISABLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class AccountLifecycleHistory:
    principal_id: str
    events: tuple[AccountLifecycleEvent, ...] = ()

    def __post_init__(self) -> None:
        _require_texts(principal_id=self.principal_id)
        if not isinstance(self.events, tuple):
            raise TypeError("lifecycle events must be an immutable tuple")
        if self.events and self.events[0].from_state is not AccountLifecycleState.UNRECONCILED:
            raise ValueError("lifecycle history must begin at the UNRECONCILED anchor")
        if any(event.principal_id != self.principal_id for event in self.events):
            raise ValueError("lifecycle history cannot cross principal boundaries")
        for previous, current in zip(self.events, self.events[1:]):
            if previous.to_state is not current.from_state:
                raise ValueError("lifecycle history has a discontinuous state transition")
            if previous.occurred_at > current.occurred_at:
                raise ValueError("lifecycle events must be chronologically ordered")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("lifecycle event ids must be unique")

    @property
    def current_state(self) -> AccountLifecycleState:
        """A missing event history is explicitly ineligible, never ACTIVE."""
        return self.events[-1].to_state if self.events else AccountLifecycleState.UNRECONCILED

    @property
    def maos_effect_eligible(self) -> bool:
        return self.current_state is AccountLifecycleState.ACTIVE


def append_lifecycle_event(
    history: AccountLifecycleHistory, event: AccountLifecycleEvent
) -> AccountLifecycleHistory:
    """Return an append-only logical history; identical event replay is idempotent."""
    if event.principal_id != history.principal_id:
        raise ValueError("lifecycle event principal does not match history")
    for existing in history.events:
        if existing.event_id == event.event_id:
            if existing == event:
                return history
            raise ValueError("lifecycle event id was reused with different content")
    if event.from_state is not history.current_state:
        raise ValueError("lifecycle event does not continue current state")
    if history.events and event.occurred_at < history.events[-1].occurred_at:
        raise ValueError("lifecycle event time cannot move backwards")
    return replace(history, events=(*history.events, event))


class TenantMultiplicityPolicy(StrEnum):
    EXACTLY_ONE_ACTIVE_CANONICAL = "exactly_one_active_canonical"


@dataclass(frozen=True, slots=True)
class TenantPolicyContractV1:
    policy: TenantMultiplicityPolicy = TenantMultiplicityPolicy.EXACTLY_ONE_ACTIVE_CANONICAL
    required_active_memberships: int = 1
    multi_tenant_selection_enabled: bool = False

    def __post_init__(self) -> None:
        if (
            self.policy is not TenantMultiplicityPolicy.EXACTLY_ONE_ACTIVE_CANONICAL
            or self.required_active_memberships != 1
            or self.multi_tenant_selection_enabled
        ):
            raise ValueError("MAOS tenant policy V1 is exact-one and disables tenant selection")


TENANT_POLICY_V1 = TenantPolicyContractV1()


@dataclass(frozen=True, slots=True)
class CanonicalTenantBinding:
    principal_id: str
    tenant_id: str
    membership_ref: str

    def __post_init__(self) -> None:
        _require_texts(
            principal_id=self.principal_id,
            tenant_id=self.tenant_id,
            membership_ref=self.membership_ref,
        )


@dataclass(frozen=True, slots=True)
class ApproverGrant:
    grant_id: str
    approver_principal_id: str
    issuer_principal_id: str
    risk_tiers: frozenset[RiskClass]
    issued_at: datetime
    expires_at: datetime
    grant_ref: str
    revocation_ref: str | None = None

    def __post_init__(self) -> None:
        _require_texts(
            grant_id=self.grant_id,
            approver_principal_id=self.approver_principal_id,
            issuer_principal_id=self.issuer_principal_id,
            grant_ref=self.grant_ref,
        )
        _require_aware(self.issued_at, "approver grant issued_at")
        _require_aware(self.expires_at, "approver grant expires_at")
        if self.expires_at <= self.issued_at:
            raise ValueError("approver grant validity interval must be positive")
        if not isinstance(self.risk_tiers, frozenset) or not self.risk_tiers:
            raise TypeError("approver risk tiers must be a non-empty frozenset")
        if RiskClass.CRITICAL in self.risk_tiers:
            raise ValueError("CRITICAL approvals are disabled in MAOS V1")
        if any(tier not in {RiskClass.HIGH} for tier in self.risk_tiers):
            raise ValueError("approver grants may authorize HIGH only in MAOS V1")
        if self.revocation_ref is not None and not self.revocation_ref.strip():
            raise ValueError("revocation reference cannot be empty")

    def valid_for(self, *, approver_id: str, risk: RiskClass, at: datetime) -> bool:
        return (
            self.revocation_ref is None
            and approver_id == self.approver_principal_id
            and risk in self.risk_tiers
            and self.issued_at <= at < self.expires_at
        )


class ApprovalState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


_APPROVAL_TERMINAL = frozenset(
    {ApprovalState.REJECTED, ApprovalState.CONSUMED, ApprovalState.EXPIRED, ApprovalState.REVOKED}
)
_APPROVAL_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.REQUESTED: frozenset(
        {ApprovalState.APPROVED, ApprovalState.REJECTED, ApprovalState.EXPIRED, ApprovalState.REVOKED}
    ),
    ApprovalState.APPROVED: frozenset(
        {ApprovalState.CONSUMED, ApprovalState.EXPIRED, ApprovalState.REVOKED}
    ),
    ApprovalState.REJECTED: frozenset(),
    ApprovalState.CONSUMED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
    ApprovalState.REVOKED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    approval_id: str
    requester_principal_id: str
    operation_digest: str
    risk_class: RiskClass
    state: ApprovalState
    requested_at: datetime
    expires_at: datetime
    approver_principal_id: str | None = None
    approver_grant_ref: str | None = None
    last_event_ref: str | None = None

    def __post_init__(self) -> None:
        _require_texts(
            approval_id=self.approval_id,
            requester_principal_id=self.requester_principal_id,
            operation_digest=self.operation_digest,
        )
        _require_digest(self.operation_digest, "approval operation_digest")
        _require_aware(self.requested_at, "approval requested_at")
        _require_aware(self.expires_at, "approval expires_at")
        if self.expires_at <= self.requested_at:
            raise ValueError("approval validity interval must be positive")
        if self.state is ApprovalState.APPROVED and not all(
            (self.approver_principal_id, self.approver_grant_ref)
        ):
            raise ValueError("approved records require an approver and grant reference")
        if self.approver_principal_id is not None and not self.approver_principal_id.strip():
            raise ValueError("approver principal cannot be empty")
        if self.approver_grant_ref is not None and not self.approver_grant_ref.strip():
            raise ValueError("approver grant reference cannot be empty")


def transition_approval(
    record: ApprovalRecord,
    target: ApprovalState,
    *,
    actor_principal_id: str,
    event_ref: str,
    occurred_at: datetime,
    approver_grant: ApproverGrant | None = None,
) -> ApprovalRecord:
    """Apply one valid approval transition; terminal states cannot be replayed."""
    _require_texts(actor_principal_id=actor_principal_id, event_ref=event_ref)
    _require_aware(occurred_at, "approval event time")
    if target not in _APPROVAL_TRANSITIONS[record.state]:
        raise ValueError("invalid approval lifecycle transition or terminal-state replay")
    if record.risk_class is RiskClass.CRITICAL:
        raise ValueError("CRITICAL external effects and approvals are disabled in MAOS V1")
    if occurred_at < record.requested_at:
        raise ValueError("approval event cannot precede request")
    if occurred_at >= record.expires_at and target is not ApprovalState.EXPIRED:
        raise ValueError("approval is expired")
    if target is ApprovalState.EXPIRED and occurred_at < record.expires_at:
        raise ValueError("approval cannot expire before its expiry time")
    if target is ApprovalState.APPROVED:
        if record.risk_class is not RiskClass.HIGH:
            raise ValueError("V1 human approval applies only to HIGH risk")
        if actor_principal_id == record.requester_principal_id:
            raise ValueError("requester cannot approve their own operation")
        if approver_grant is None or not approver_grant.valid_for(
            approver_id=actor_principal_id, risk=record.risk_class, at=occurred_at
        ):
            raise ValueError("a valid, non-revoked human ApproverGrant is required")
        return replace(
            record,
            state=target,
            approver_principal_id=actor_principal_id,
            approver_grant_ref=approver_grant.grant_ref,
            last_event_ref=event_ref,
        )
    if target is ApprovalState.CONSUMED and actor_principal_id != record.approver_principal_id:
        raise ValueError("only the recorded approver may consume this approval contract")
    return replace(record, state=target, last_event_ref=event_ref)


def critical_effects_enabled_v1() -> bool:
    """CRITICAL external effects are unconditionally disabled for MAOS V1."""
    return False


@dataclass(frozen=True, slots=True)
class RiskPolicyIdentity:
    policy_id: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        _require_texts(policy_id=self.policy_id, version=self.version)
        _require_digest(self.digest, "risk policy digest")


@dataclass(frozen=True, slots=True)
class RiskPolicyActivation:
    identity: RiskPolicyIdentity
    release_ref: str
    manager_approval_ref: str
    activated_at: datetime

    def __post_init__(self) -> None:
        _require_texts(release_ref=self.release_ref, manager_approval_ref=self.manager_approval_ref)
        _require_aware(self.activated_at, "risk policy activation time")


def authoritative_risk(
    policy_risk: RiskClass | None, agent_risks: tuple[RiskClass, ...] = ()
) -> RiskClass:
    """Agent inputs can raise but never lower risk; missing policy fails closed."""
    if policy_risk is None:
        return RiskClass.CRITICAL
    if not isinstance(agent_risks, tuple):
        raise TypeError("agent risks must be an immutable tuple")
    rank = {
        RiskClass.LOW: 0,
        RiskClass.MEDIUM: 1,
        RiskClass.HIGH: 2,
        RiskClass.CRITICAL: 3,
    }
    return max((policy_risk, *agent_risks), key=rank.__getitem__)


class AuditAction(StrEnum):
    APPEND = "append"
    ARCHIVE = "archive"
    DELETE = "delete"
    PURGE = "purge"


@dataclass(frozen=True, slots=True)
class AuditPolicyV1:
    automatic_deletion_enabled: bool = False
    purge_enabled: bool = False

    def __post_init__(self) -> None:
        if self.automatic_deletion_enabled or self.purge_enabled:
            raise ValueError("automatic audit deletion and purge are disabled in V1")

    def permits(
        self, action: AuditAction, qualification: ArchiveQualification | None = None
    ) -> bool:
        if action is AuditAction.APPEND:
            return True
        if action is AuditAction.ARCHIVE:
            return qualification is not None and qualification.eligible
        return False


AUDIT_POLICY_V1 = AuditPolicyV1()


@dataclass(frozen=True, slots=True)
class ArchiveQualification:
    integrity_verified: bool
    restore_verified: bool
    references_preserved: bool

    @property
    def eligible(self) -> bool:
        return self.integrity_verified and self.restore_verified and self.references_preserved


@dataclass(frozen=True, slots=True)
class AuthorityAuditEvent:
    event_id: str
    actor_principal_ref: str
    action: str
    resource_ref: str
    operation_digest: str
    policy_identity: RiskPolicyIdentity
    occurred_at: datetime

    def __post_init__(self) -> None:
        _require_texts(
            event_id=self.event_id,
            actor_principal_ref=self.actor_principal_ref,
            action=self.action,
            resource_ref=self.resource_ref,
        )
        _require_digest(self.operation_digest, "audit operation_digest")
        _require_aware(self.occurred_at, "audit event time")


@dataclass(frozen=True, slots=True)
class EffectIntent:
    intent_id: str
    operation_digest: str
    authority_decision_ref: str
    audit_event_ref: str
    capability: Capability
    risk_class: RiskClass

    def __post_init__(self) -> None:
        _require_texts(
            intent_id=self.intent_id,
            authority_decision_ref=self.authority_decision_ref,
            audit_event_ref=self.audit_event_ref,
        )
        _require_digest(self.operation_digest, "effect intent operation_digest")
        if self.risk_class is RiskClass.CRITICAL:
            raise ValueError("CRITICAL external effects are disabled in MAOS V1")


@dataclass(frozen=True, slots=True)
class DelegationScope:
    capabilities: frozenset[Capability]
    resource_refs: frozenset[str]
    maximum_risk: RiskClass

    def __post_init__(self) -> None:
        if not isinstance(self.capabilities, frozenset) or not self.capabilities:
            raise TypeError("delegated capabilities must be a non-empty frozenset")
        if any(not isinstance(item, Capability) for item in self.capabilities):
            raise TypeError("delegated capabilities must use canonical capability values")
        if not isinstance(self.resource_refs, frozenset) or not self.resource_refs:
            raise TypeError("delegated resources must be a non-empty frozenset")
        if any(not item.strip() or "*" in item for item in self.resource_refs):
            raise ValueError("delegated resource scope must use exact references")
        if not isinstance(self.maximum_risk, RiskClass):
            raise TypeError("delegated maximum risk must use a canonical risk value")


@dataclass(frozen=True, slots=True)
class DelegationGrant:
    delegation_id: str
    parent_authority_ref: str
    issuer_principal_id: str
    delegate_principal_id: str
    scope: DelegationScope
    issued_at: datetime
    expires_at: datetime
    revocation_ref: str | None = None
    transitive: bool = False

    def __post_init__(self) -> None:
        _require_texts(
            delegation_id=self.delegation_id,
            parent_authority_ref=self.parent_authority_ref,
            issuer_principal_id=self.issuer_principal_id,
            delegate_principal_id=self.delegate_principal_id,
        )
        _require_aware(self.issued_at, "delegation issued_at")
        _require_aware(self.expires_at, "delegation expires_at")
        if self.expires_at <= self.issued_at:
            raise ValueError("delegation validity interval must be positive")
        if self.revocation_ref is not None and not self.revocation_ref.strip():
            raise ValueError("delegation revocation reference cannot be empty")
        if self.transitive:
            raise ValueError("delegation is non-transitive in MAOS V1")


def delegation_is_eligible(
    grant: DelegationGrant | None,
    *,
    parent_scope: DelegationScope | None,
    requested_scope: DelegationScope,
    at: datetime,
) -> bool:
    """Pure scope/expiry check; caller must obtain grant and parent state authoritatively."""
    _require_aware(at, "delegation check time")
    if grant is None or parent_scope is None or grant.revocation_ref is not None or grant.transitive:
        return False
    if not grant.issued_at <= at < grant.expires_at:
        return False
    return _scope_contains(parent_scope, grant.scope) and _scope_contains(grant.scope, requested_scope)


def _scope_contains(parent: DelegationScope, child: DelegationScope) -> bool:
    rank = {
        RiskClass.LOW: 0,
        RiskClass.MEDIUM: 1,
        RiskClass.HIGH: 2,
        RiskClass.CRITICAL: 3,
    }
    return (
        child.capabilities <= parent.capabilities
        and child.resource_refs <= parent.resource_refs
        and rank[child.maximum_risk] <= rank[parent.maximum_risk]
    )


def _require_texts(**values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("required authority contract references cannot be empty")


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_digest(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
