from dataclasses import dataclass
from typing import Literal

CanonicalRole = Literal["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"]

@dataclass(frozen=True)
class AdminScope:
    subject: str
    role: CanonicalRole
    tenant_id: str | None


def authorize_scope(*, principal: AdminScope, requested_tenant: str | None) -> bool:
    """Fail-closed scope decision used before executing an admin query."""
    if principal.role == "SUPER_ADMIN":
        return requested_tenant is None or bool(requested_tenant)
    if principal.role in ("SCHOOL_ADMIN", "TEACHER"):
        return bool(principal.tenant_id and requested_tenant and principal.tenant_id == requested_tenant)
    return False


def require_scope(*, principal: AdminScope, requested_tenant: str | None) -> str:
    if not authorize_scope(principal=principal, requested_tenant=requested_tenant):
        raise PermissionError("TENANT_SCOPE_REQUIRED")
    return requested_tenant or principal.tenant_id or "*"
