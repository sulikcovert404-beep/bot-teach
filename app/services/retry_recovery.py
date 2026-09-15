"""Provider-neutral retry and recovery contracts (contract-only)."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import json, unicodedata
from collections.abc import Mapping

class FailureCategory(StrEnum):
    TRANSIENT="TRANSIENT"; PERMANENT="PERMANENT"; AMBIGUOUS="AMBIGUOUS"; POLICY_BLOCKED="POLICY_BLOCKED"
class RetryOutcome(StrEnum):
    RETRY_ALLOWED="RETRY_ALLOWED"; RETRY_DENIED="RETRY_DENIED"; RETRY_DEFERRED="RETRY_DEFERRED"; MANUAL_REVIEW="MANUAL_REVIEW"
class RecoveryAction(StrEnum):
    RETRY="RETRY"; RECONCILE="RECONCILE"; RESUME="RESUME"; RESTART="RESTART"; CANCEL="CANCEL"; ESCALATE="ESCALATE"

def _nfc(value: str) -> str: return unicodedata.normalize("NFC", value)
def _canonical(value: object) -> str: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

@dataclass(frozen=True, slots=True)
class FailureClassification:
    category: FailureCategory
    reason_code: str
    phase: str
    operation: str
    policy_reference: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_code", _nfc(self.reason_code))
        object.__setattr__(self, "phase", _nfc(self.phase)); object.__setattr__(self, "operation", _nfc(self.operation))
    def canonical_json(self) -> str:
        return _canonical({"category": self.category.value, "metadata": dict(self.metadata), "operation": self.operation, "phase": self.phase, "policy_reference": self.policy_reference, "reason_code": self.reason_code})

@dataclass(frozen=True, slots=True)
class RetryDecision:
    outcome: RetryOutcome
    reason_code: str
    source_status: str
    attempt_reference: str
    policy_reference: str | None = None
    max_attempts: int | None = None
    deadline_reference: str | None = None
    def __post_init__(self) -> None:
        if self.max_attempts is not None and self.max_attempts < 1: raise ValueError("max_attempts must be positive")
        for name in ("reason_code", "source_status", "attempt_reference", "policy_reference", "deadline_reference"):
            value = getattr(self, name)
            if value is not None: object.__setattr__(self, name, _nfc(value))
    def canonical_json(self) -> str:
        return _canonical({"attempt_reference": self.attempt_reference, "deadline_reference": self.deadline_reference, "max_attempts": self.max_attempts, "outcome": self.outcome.value, "policy_reference": self.policy_reference, "reason_code": self.reason_code, "source_status": self.source_status})

def decide_retry(classification: FailureClassification, *, attempt_reference: str, max_attempts: int | None = None, deadline_reference: str | None = None) -> RetryDecision:
    if classification.category is FailureCategory.TRANSIENT:
        return RetryDecision(RetryOutcome.RETRY_ALLOWED, classification.reason_code, classification.category.value, attempt_reference, classification.policy_reference, max_attempts, deadline_reference)
    if classification.category is FailureCategory.AMBIGUOUS:
        return RetryDecision(RetryOutcome.RETRY_DEFERRED, "RECONCILE_FIRST", classification.category.value, attempt_reference, classification.policy_reference, max_attempts, deadline_reference)
    if classification.category is FailureCategory.POLICY_BLOCKED:
        return RetryDecision(RetryOutcome.MANUAL_REVIEW, classification.reason_code, classification.category.value, attempt_reference, classification.policy_reference, max_attempts, deadline_reference)
    return RetryDecision(RetryOutcome.RETRY_DENIED, classification.reason_code, classification.category.value, attempt_reference, classification.policy_reference, max_attempts, deadline_reference)

def recovery_action(classification: FailureClassification) -> RecoveryAction:
    return {FailureCategory.TRANSIENT: RecoveryAction.RETRY, FailureCategory.PERMANENT: RecoveryAction.CANCEL, FailureCategory.AMBIGUOUS: RecoveryAction.RECONCILE, FailureCategory.POLICY_BLOCKED: RecoveryAction.ESCALATE}[classification.category]
