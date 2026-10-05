"""Pure capability grant evaluation; no grant issuer or execution adapter."""

from dataclasses import dataclass
from datetime import datetime

from app.maos.kernel_v1.models import Capability, RiskClass
from app.maos.kernel_v1.tenant import TenantAuthorizationContext


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    grant_id: str
    task_id: str
    principal_id: str
    tenant_id: str
    capability: Capability
    resource_scope: frozenset[str]
    risk_class: RiskClass
    issuer: str
    issued_at: datetime
    expires_at: datetime
    constraints: frozenset[str]
    policy_version: str
    revocation_ref: str | None = None

    def __post_init__(self) -> None:
        if not all((self.grant_id, self.task_id, self.principal_id, self.tenant_id, self.issuer, self.policy_version)):
            raise ValueError("grant identity and issuer references are required")
        if not self.resource_scope or any(not resource.strip() or "*" in resource for resource in self.resource_scope):
            raise ValueError("grant resource scope must contain exact resource identities")
        if self.expires_at.tzinfo is None or self.issued_at.tzinfo is None or self.expires_at <= self.issued_at:
            raise ValueError("grant validity interval must be timezone-aware and positive")
        if not isinstance(self.resource_scope, frozenset) or not isinstance(self.constraints, frozenset):
            raise TypeError("grant scopes and constraints must be immutable")


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    task_id: str
    principal_id: str
    capability: Capability
    resource_id: str
    risk_class: RiskClass | None
    policy_version: str
    requested_at: datetime
    tenant_context: TenantAuthorizationContext | None
    human_decision_required: bool = False
    human_decision_approved: bool = False
    forbidden_actions: frozenset[Capability] = frozenset()
    approved_grant_issuers: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not all((self.task_id, self.principal_id, self.resource_id, self.policy_version)):
            raise ValueError("authorization request identity and target are required")
        if self.requested_at.tzinfo is None:
            raise ValueError("authorization time must be timezone-aware")


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def evaluate_capability_grant(grant: CapabilityGrant | None, request: AuthorizationRequest) -> AuthorizationDecision:
    """Deny by default and require exact identity, resource, risk and policy binding."""
    if grant is None:
        return AuthorizationDecision(False, "missing_grant")
    ctx = request.tenant_context
    if ctx is None or not all((ctx.principal_id, ctx.tenant_id, ctx.purpose, ctx.authorization_ref)):
        return AuthorizationDecision(False, "missing_tenant_authority")
    if request.capability in request.forbidden_actions:
        return AuthorizationDecision(False, "forbidden_capability")
    if grant.revocation_ref:
        return AuthorizationDecision(False, "grant_revoked")
    if not grant.issuer or grant.issuer not in request.approved_grant_issuers:
        return AuthorizationDecision(False, "unqualified_grant_issuer")
    if request.requested_at < grant.issued_at or request.requested_at >= grant.expires_at:
        return AuthorizationDecision(False, "grant_expired_or_not_yet_valid")
    if request.risk_class is None:
        return AuthorizationDecision(False, "unknown_risk")
    if request.human_decision_required and not request.human_decision_approved:
        return AuthorizationDecision(False, "human_decision_required")
    if (
        grant.task_id != request.task_id
        or grant.principal_id != request.principal_id
        or grant.principal_id != ctx.principal_id
        or grant.tenant_id != ctx.tenant_id
        or grant.capability is not request.capability
        or request.resource_id not in grant.resource_scope
        or grant.risk_class is not request.risk_class
        or grant.policy_version != request.policy_version
        or grant.policy_version != ctx.policy_version
    ):
        return AuthorizationDecision(False, "grant_scope_mismatch")
    return AuthorizationDecision(True, "grant_valid")
