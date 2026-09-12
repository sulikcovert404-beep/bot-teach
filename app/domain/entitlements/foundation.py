"""Provider-neutral role, plan, and entitlement foundation.

Pure policy objects; persistence and billing adapters are intentionally out of scope.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class Plan(StrEnum):
    STUDENT_FREE = "STUDENT_FREE"
    STUDENT_PRO = "STUDENT_PRO"
    TEACHER_FREE = "TEACHER_FREE"
    SCHOOL_FREE = "SCHOOL_FREE"


class AccessDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    EXPIRED = "EXPIRED"

class ClassroomContentAccess(StrEnum):
    DENY = "DENY"
    PREVIEW = "PREVIEW"
    FULL = "FULL"
    LOCKED = "LOCKED"

def resolve_classroom_content_access(*, is_member: bool, plan: str | None, active_until: datetime | None = None, published: bool = True, now: datetime | None = None) -> ClassroomContentAccess:
    """Resolve classroom content access centrally; membership always precedes plan."""
    if not is_member or not published:
        return ClassroomContentAccess.DENY
    current = now or datetime.now(UTC)
    if active_until is not None:
        expiry = active_until if active_until.tzinfo else active_until.replace(tzinfo=UTC)
        if expiry <= current:
            return ClassroomContentAccess.PREVIEW
    if plan in {"STUDENT_PRO", "STUDENT_PLUS", "PRO"}:
        return ClassroomContentAccess.FULL
    if plan in {None, "FREE", "STUDENT_FREE"}:
        return ClassroomContentAccess.PREVIEW
    return ClassroomContentAccess.LOCKED


@dataclass(frozen=True)
class UserEntitlement:
    user_id: str
    role: Role
    plan: Plan
    entitlements: frozenset[str]
    active_until: datetime | None = None
    tenant_id: str | None = None


@dataclass(frozen=True)
class AccessRequest:
    action: str
    resource_tenant_id: str | None = None
    quota_available: bool = True
    now: datetime | None = None


@dataclass(frozen=True)
class AccessResult:
    decision: AccessDecision
    reason: str


def resolve_access(subject: UserEntitlement, request: AccessRequest) -> AccessResult:
    """Resolve one access decision with deny/expiry/tenant/quota precedence."""
    now = request.now or datetime.now(UTC)
    if subject.active_until is not None:
        expiry = subject.active_until
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if expiry <= now:
            return AccessResult(AccessDecision.EXPIRED, "plan_expired")
    if subject.tenant_id and request.resource_tenant_id and subject.tenant_id != request.resource_tenant_id:
        return AccessResult(AccessDecision.DENY, "tenant_boundary")
    if request.action not in subject.entitlements:
        return AccessResult(AccessDecision.DENY, "entitlement_missing")
    if request.action.startswith("AI_") and not request.quota_available:
        return AccessResult(AccessDecision.QUOTA_EXCEEDED, "quota_exceeded")
    return AccessResult(AccessDecision.ALLOW, "entitlement_granted")
