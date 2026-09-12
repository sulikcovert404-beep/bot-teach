"""Derived, provider-neutral failure decisions (no runtime side effects)."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import json, unicodedata

class FailureSource(StrEnum):
    VALIDATION="VALIDATION"; AUTHORIZATION="AUTHORIZATION"; POLICY="POLICY"; CONFIGURATION="CONFIGURATION"; RUNTIME="RUNTIME"; CANCELLATION="CANCELLATION"; AMBIGUOUS="AMBIGUOUS"; RECONCILIATION="RECONCILIATION"
class FailureCategory(StrEnum):
    TRANSIENT="TRANSIENT"; PERMANENT="PERMANENT"; AMBIGUOUS="AMBIGUOUS"; POLICY_BLOCKED="POLICY_BLOCKED"
class JobImpact(StrEnum): REJECTED="REJECTED"; FAILED="FAILED"; CANCELLED="CANCELLED"; AMBIGUOUS="AMBIGUOUS"; QUARANTINED="QUARANTINED"
class ExecutionOutcome(StrEnum): REFUSED="REFUSED"; FAILED="FAILED"; CANCELLED="CANCELLED"; RECONCILING="RECONCILING"; PRECONDITION_FAILED="PRECONDITION_FAILED"
class RecoveryAction(StrEnum): ABORT_NO_OP="ABORT_NO_OP"; RETRY="RETRY"; RECONCILE="RECONCILE"; ESCALATE="ESCALATE"; COMPENSATE="COMPENSATE"

def _nfc(v: str) -> str: return unicodedata.normalize("NFC", v)

@dataclass(frozen=True, slots=True)
class FailureContext:
    source: FailureSource; phase: str; operation: str; category: FailureCategory; reason_code: str; version: str = "1.0"; actor_reference: str|None = None; transaction_reference: str|None = None
    def __post_init__(self) -> None:
        for n in ("phase","operation","reason_code","version","actor_reference","transaction_reference"):
            v=getattr(self,n)
            if v is not None: object.__setattr__(self,n,_nfc(v))

@dataclass(frozen=True, slots=True)
class FailureDecision:
    source: FailureSource; phase: str; operation: str; category: FailureCategory; job_impact: JobImpact; execution_outcome: ExecutionOutcome; recovery_action: RecoveryAction; reason_code: str; version: str = "1.0"
    def canonical_json(self) -> str:
        return json.dumps({"category":self.category.value,"execution_outcome":self.execution_outcome.value,"job_impact":self.job_impact.value,"operation":self.operation,"phase":self.phase,"reason_code":self.reason_code,"recovery_action":self.recovery_action.value,"source":self.source.value,"version":self.version},ensure_ascii=False,sort_keys=True,separators=(",",":"))

def resolve_failure(context: FailureContext) -> FailureDecision:
    """Pure derived mapping; unknown combinations fail closed."""
    c=context.category
    if c is FailureCategory.AMBIGUOUS:
        impact,outcome,action=JobImpact.AMBIGUOUS,ExecutionOutcome.RECONCILING,RecoveryAction.RECONCILE
    elif c is FailureCategory.POLICY_BLOCKED:
        impact,outcome,action=JobImpact.REJECTED,ExecutionOutcome.PRECONDITION_FAILED,RecoveryAction.ESCALATE
    elif context.source is FailureSource.CANCELLATION:
        impact,outcome,action=JobImpact.CANCELLED,ExecutionOutcome.CANCELLED,RecoveryAction.COMPENSATE
    elif c is FailureCategory.TRANSIENT:
        impact,outcome,action=JobImpact.FAILED,ExecutionOutcome.FAILED,RecoveryAction.RETRY
    elif c is FailureCategory.PERMANENT:
        impact,outcome,action=JobImpact.REJECTED,ExecutionOutcome.REFUSED,RecoveryAction.ABORT_NO_OP
    else:
        raise ValueError("unknown failure category")
    return FailureDecision(context.source,context.phase,context.operation,c,impact,outcome,action,context.reason_code,context.version)
