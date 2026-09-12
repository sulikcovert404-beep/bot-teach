"""Pure, immutable governance freeze decision contract."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class FreezeOutcome(StrEnum):
    FROZEN = "FROZEN"
    FROZEN_WITH_EXCEPTIONS = "FROZEN_WITH_EXCEPTIONS"
    NOT_FROZEN = "NOT_FROZEN"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_clean(v) for v in value]
    return value


def _reject(value: Any) -> None:
    if isinstance(value, str) and _SECRET.search(value):
        raise ValueError("secret-like content is not permitted")
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET.search(str(key)):
                raise ValueError("secret-like field is not permitted")
            _reject(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _reject(item)


@dataclass(frozen=True, slots=True)
class GovernanceFreezeDecision:
    freeze_id: str
    baseline_reference: ReferenceToken
    closure_reference: ReferenceToken
    consistency_reference: ReferenceToken
    handoff_reference: ReferenceToken
    readiness_reference: ReferenceToken
    decision_reason: str
    trace_reference: ReferenceToken
    freeze_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.freeze_id or not self.decision_reason:
            raise ValueError("freeze_id and decision_reason are required")
        _reject(self.payload())
        if self.freeze_digest and self.freeze_digest != self.compute_digest():
            raise ValueError("freeze digest mismatch")
        if not self.freeze_digest:
            object.__setattr__(self, "freeze_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {k: v.to_dict() if isinstance(v, ReferenceToken) else v for k, v in {
            "freeze_id": self.freeze_id, "baseline_reference": self.baseline_reference,
            "closure_reference": self.closure_reference, "consistency_reference": self.consistency_reference,
            "handoff_reference": self.handoff_reference, "readiness_reference": self.readiness_reference,
            "decision_reason": self.decision_reason, "trace_reference": self.trace_reference,
        }.items()}

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.freeze_digest == self.compute_digest()


def evaluate_freeze(decision: GovernanceFreezeDecision) -> FreezeOutcome:
    refs = (decision.baseline_reference, decision.closure_reference, decision.consistency_reference,
            decision.handoff_reference, decision.readiness_reference)
    if not decision.digest_matches():
        return FreezeOutcome.NOT_FROZEN
    if any(r.status is ReferenceStatus.BLOCKED for r in refs):
        return FreezeOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs):
        return FreezeOutcome.NOT_FROZEN
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs):
        return FreezeOutcome.UNKNOWN
    if decision.trace_reference.status is ReferenceStatus.INVALID:
        return FreezeOutcome.NOT_FROZEN
    if decision.trace_reference.status is not ReferenceStatus.VALID:
        return FreezeOutcome.FROZEN_WITH_EXCEPTIONS
    return FreezeOutcome.FROZEN
