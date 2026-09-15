"""Pure immutable release-readiness decision contract."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")

class ReadinessOutcome(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"

class ContractState(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    REQUIRES_REVALIDATION = "REQUIRES_REVALIDATION"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)

def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return _nfc(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_clean(v) for v in value]
    if isinstance(value, StrEnum):
        return value.value
    return value

def _bytes(value: Any) -> bytes:
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_bytes(value)).hexdigest()

def _validate_texts(value: Any) -> None:
    if isinstance(value, str):
        if _SECRET.search(value):
            raise ValueError("secret-like content is not permitted")
    elif isinstance(value, dict):
        for k, v in value.items():
            if _SECRET.search(str(k)):
                raise ValueError("secret-like field is not permitted")
            _validate_texts(v)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for v in value:
            _validate_texts(v)

@dataclass(frozen=True, slots=True)
class ReleaseReadinessDecision:
    release_reference: str
    evaluated_contracts: tuple[str, ...]
    evidence_summary: tuple[str, ...]
    validation_summary: tuple[str, ...]
    transition_summary: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    trace_reference: str = ""
    decision_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_texts(self.payload())
        for name in ("release_reference", "trace_reference"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if any(not isinstance(x, str) or not x for group in (self.evaluated_contracts, self.evidence_summary, self.validation_summary, self.transition_summary, self.blockers) for x in group):
            raise ValueError("summary entries must be non-empty strings")
        if self.decision_digest and self.decision_digest != self.compute_digest():
            raise ValueError("digest mismatch")
        if not self.decision_digest:
            object.__setattr__(self, "decision_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"release_reference": self.release_reference, "evaluated_contracts": self.evaluated_contracts, "evidence_summary": self.evidence_summary, "validation_summary": self.validation_summary, "transition_summary": self.transition_summary, "blockers": self.blockers, "trace_reference": self.trace_reference}
    def canonical_bytes(self) -> bytes:
        return _bytes(self.payload())
    def compute_digest(self) -> str:
        return _digest(self.payload())
    def verify_digest(self) -> bool:
        return self.decision_digest == self.compute_digest()


def resolve_readiness(*, release_reference: str, evaluated_contracts: Iterable[str], evidence_summary: Iterable[str], validation_summary: Iterable[str], transition_summary: Iterable[str], blockers: Iterable[str] = (), trace_reference: str, evidence_state: str = "VALID", validation_state: str = "VALID", transition_state: str = "COMPATIBLE", digest_match: bool = True) -> tuple[ReadinessOutcome, ReleaseReadinessDecision]:
    ev = tuple(evidence_summary); val = tuple(validation_summary); trans = tuple(transition_summary); bl = tuple(blockers); contracts = tuple(evaluated_contracts)
    decision = ReleaseReadinessDecision(release_reference, contracts, ev, val, trans, bl, trace_reference)
    if not digest_match:
        return ReadinessOutcome.REQUIRES_REVIEW, decision
    if transition_state == ContractState.INCOMPATIBLE or validation_state in {"FAILED", "INCOMPATIBLE"}:
        return ReadinessOutcome.NOT_READY, decision
    if bl or evidence_state == "BLOCKED" or validation_state == "BLOCKED":
        return ReadinessOutcome.BLOCKED, decision
    if evidence_state in {"UNKNOWN", "STALE"} or validation_state in {"UNKNOWN", "STALE"} or transition_state in {ContractState.UNKNOWN, ContractState.REQUIRES_REVALIDATION}:
        return ReadinessOutcome.REQUIRES_REVIEW, decision
    if evidence_state != "VALID" or validation_state != "VALID" or transition_state != ContractState.COMPATIBLE:
        return ReadinessOutcome.REQUIRES_REVIEW, decision
    return ReadinessOutcome.READY, decision
