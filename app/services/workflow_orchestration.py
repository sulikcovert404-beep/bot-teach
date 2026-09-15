"""Database-free orchestration boundary for admin content commands."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Any
from collections.abc import Callable

from .admin_authorization import Actor, AuthorizationContext, authorize
from .content_commands import _Command
from .curriculum_pipeline_api import ContentValidationError
from .content_commands import ApproveContentVersionCommand, PublishRequestContract


class WorkflowStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    VALIDATION_FAILED = "validation_failed"
    UNAUTHORIZED = "unauthorized"


@dataclass(frozen=True)
class WorkflowResult:
    status: WorkflowStatus
    command: str
    receipt: str
    reason: str | None = None

    def serialize(self) -> str:
        """Return a stable UTF-8 JSON representation for receipts and logs."""
        return json.dumps(
            {
                "command": self.command,
                "receipt": self.receipt,
                "reason": self.reason,
                "status": self.status.value,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


class WorkflowDispatcher:
    def __init__(self) -> None:
        self._receipts: dict[str, tuple[str, WorkflowResult]] = {}

    def dispatch(
        self,
        command: _Command,
        actor: Actor,
        context: AuthorizationContext,
        execute: Callable[[_Command], Any] | None = None,
    ) -> WorkflowResult:
        key = command.idempotency_key
        if key in self._receipts:
            old_hash, result = self._receipts[key]
            if old_hash != command.request_hash:
                return WorkflowResult(WorkflowStatus.CONFLICT, type(command).__name__, "", "idempotency_conflict")
            return result
        decision = authorize(command, actor, context)
        if not decision.allowed:
            result = WorkflowResult(WorkflowStatus.UNAUTHORIZED, type(command).__name__, "", decision.reason_code)
        else:
            try:
                if isinstance(command, ApproveContentVersionCommand) and context.processing_state not in (None, "VALIDATED"):
                    raise ContentValidationError("approval requires VALIDATED processing state")
                if isinstance(command, PublishRequestContract):
                    if context.review_state not in (None, "APPROVED") or context.vector_sync_state not in (None, "VECTOR_SYNCED"):
                        raise ContentValidationError("publication prerequisites are not satisfied")
                    if context.digest is not None and command.request_hash != context.digest:
                        raise ContentValidationError("publication digest mismatch")
                if execute is not None:
                    execute(command)
                result = WorkflowResult(WorkflowStatus.ACCEPTED, type(command).__name__, command.request_hash)
            except ContentValidationError as exc:
                result = WorkflowResult(WorkflowStatus.VALIDATION_FAILED, type(command).__name__, "", str(exc))
            except (ValueError, RuntimeError) as exc:
                result = WorkflowResult(WorkflowStatus.REJECTED, type(command).__name__, "", str(exc))
        self._receipts[key] = (command.request_hash, result)
        return result
