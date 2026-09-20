"""Pure authorization policy for the admin content workflow.

The module deliberately has no persistence or web-framework dependencies.  It
evaluates a fully assembled context and returns a deterministic decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    CREATOR = "creator"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    ADMINISTRATOR = "administrator"


class PrincipalType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"


@dataclass(frozen=True)
class Actor:
    actor_id: str
    roles: frozenset[Role]
    principal_type: PrincipalType = PrincipalType.HUMAN


@dataclass(frozen=True)
class AuthorizationContext:
    creator_id: str | None = None
    lifecycle_state: str | None = None
    processing_state: str | None = None
    review_state: str | None = None
    vector_sync_state: str | None = None
    digest: str | None = None


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str | None = None
    policy_version: str = "admin-auth-v1"


_COMMAND_ROLES: dict[str, frozenset[Role]] = {
    "CreateContentVersionCommand": frozenset({Role.CREATOR}),
    "UpdateContentMetadataCommand": frozenset({Role.CREATOR}),
    "SubmitProcessingCommand": frozenset({Role.CREATOR}),
    "ApproveContentVersionCommand": frozenset({Role.REVIEWER}),
    "RejectContentVersionCommand": frozenset({Role.REVIEWER}),
    "PublishRequestContract": frozenset({Role.PUBLISHER, Role.ADMINISTRATOR}),
}


def authorize(command: Any, actor: Actor, context: AuthorizationContext) -> AuthorizationDecision:
    """Evaluate policy without I/O, clocks, or exceptions."""
    command_name = type(command).__name__
    if not actor.actor_id or actor.principal_type is not PrincipalType.HUMAN:
        return AuthorizationDecision(False, "invalid_actor")
    required = _COMMAND_ROLES.get(command_name)
    if required is None:
        return AuthorizationDecision(False, "unknown_command")
    if not actor.roles.intersection(required):
        return AuthorizationDecision(False, "missing_role")
    if command_name in {"ApproveContentVersionCommand", "RejectContentVersionCommand"}:
        if context.creator_id is not None and context.creator_id == actor.actor_id:
            return AuthorizationDecision(False, "maker_checker_violation")
        if context.lifecycle_state not in {"VALIDATED", "PENDING_REVIEW"}:
            return AuthorizationDecision(False, "invalid_ownership")
    if (
        command_name in {"CreateContentVersionCommand", "UpdateContentMetadataCommand", "SubmitProcessingCommand"}
        and context.creator_id is not None
        and context.creator_id != actor.actor_id
    ):
        return AuthorizationDecision(False, "invalid_ownership")
    if command_name == "PublishRequestContract" and context.lifecycle_state != "APPROVED":
        return AuthorizationDecision(False, "forbidden_transition")
    return AuthorizationDecision(True)
