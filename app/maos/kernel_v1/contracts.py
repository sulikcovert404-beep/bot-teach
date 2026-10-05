"""Pure structural and reference validation before planning/dispatch."""

from dataclasses import dataclass
from datetime import datetime

from app.maos.kernel_v1.models import TaskEnvelopeV1
from app.maos.kernel_v1.tenant import TenantAuthorizationContext


@dataclass(frozen=True, slots=True)
class EnvelopeValidationContext:
    checked_at: datetime
    tenant_authorization: TenantAuthorizationContext | None
    available_grant_refs: frozenset[str]


@dataclass(frozen=True, slots=True)
class EnvelopeValidationResult:
    valid: bool
    errors: tuple[str, ...]


def validate_task_envelope(envelope: TaskEnvelopeV1, context: EnvelopeValidationContext) -> EnvelopeValidationResult:
    """Check temporal, tenant and grant references; never resolve or create authority."""
    errors: list[str] = []
    checked_at = context.checked_at
    if checked_at.tzinfo is None:
        errors.append("validation_time_not_timezone_aware")
    elif checked_at >= envelope.expires_at:
        errors.append("envelope_expired")
    elif checked_at >= envelope.deadline:
        errors.append("task_deadline_elapsed")
    tenant = context.tenant_authorization
    if tenant is None:
        errors.append("tenant_authority_unresolved")
    elif (
        tenant.principal_id != envelope.principal_id
        or tenant.tenant_id != envelope.tenant_id
        or tenant.purpose != envelope.purpose
    ):
        errors.append("tenant_authority_scope_mismatch")
    if set(envelope.capability_grant_refs) - context.available_grant_refs:
        errors.append("capability_grant_reference_missing")
    return EnvelopeValidationResult(not errors, tuple(errors))
