"""Authorization wiring foundation using the existing provider-neutral policy."""
from dataclasses import dataclass
from typing import Any

from .admin_authorization import Actor, AuthorizationContext, AuthorizationDecision, authorize


@dataclass(frozen=True)
class AuthorizationAuditRecord:
    command_name: str
    actor_id: str
    allowed: bool
    reason_code: str | None
    policy_version: str


def evaluate_content_access(command: Any, actor: Actor, context: AuthorizationContext) -> AuthorizationAuditRecord:
    """Evaluate and return an auditable decision without changing permissions."""
    decision: AuthorizationDecision = authorize(command, actor, context)
    return AuthorizationAuditRecord(type(command).__name__, actor.actor_id,
                                    decision.allowed, decision.reason_code,
                                    decision.policy_version)
