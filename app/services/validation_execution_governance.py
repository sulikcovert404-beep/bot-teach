"""Pure immutable governance evaluator for future validation execution."""
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class GovernanceOutcome(StrEnum):
    ALLOWED = "ALLOWED"; DENIED = "DENIED"; BLOCKED = "BLOCKED"; REQUIRES_REVIEW = "REQUIRES_REVIEW"
class GovernanceError(ValueError): pass
class DigestMismatchError(GovernanceError): pass
class SecretLikeValueError(GovernanceError): pass
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+|bearer\s+[A-Za-z0-9._~+/=-]{12,}")
def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise GovernanceError(f"{name} must be non-empty")
    return unicodedata.normalize("NFC", value)
def _safe(values: tuple[str, ...]) -> None:
    if any(_SECRET.search(v) for v in values): raise SecretLikeValueError("secret-like value is not permitted")

@dataclass(frozen=True, slots=True)
class ValidationExecutionRequest:
    validation_id: str; plan_version: str; requester_reference: str; authorization_context: str
    required_capabilities: tuple[str, ...]; evidence_expectation: str; request_digest: str
    def __post_init__(self) -> None:
        for n in ("validation_id", "plan_version", "requester_reference", "authorization_context", "evidence_expectation", "request_digest"):
            object.__setattr__(self, n, _text(getattr(self, n), n))
        caps = self.required_capabilities if not isinstance(self.required_capabilities, str) else (self.required_capabilities,)
        object.__setattr__(self, "required_capabilities", tuple(sorted({_text(x, "required_capabilities") for x in caps})))
        _safe((self.requester_reference, self.authorization_context, self.evidence_expectation, *self.required_capabilities))
    def as_dict(self) -> dict[str, object]:
        return {"authorization_context": self.authorization_context, "evidence_expectation": self.evidence_expectation, "plan_version": self.plan_version, "requester_reference": self.requester_reference, "required_capabilities": list(self.required_capabilities), "request_digest": self.request_digest, "validation_id": self.validation_id}
    def canonical_bytes(self) -> bytes: return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def computed_digest(self) -> str: return hashlib.sha256(self.canonical_bytes()).hexdigest()
    def verify_digest(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_digest) or self.computed_digest() != self.request_digest: raise DigestMismatchError("request digest mismatch")

@dataclass(frozen=True, slots=True)
class GovernanceDecision:
    outcome: GovernanceOutcome; reason: str; request_reference: str; decision_reference: str; evidence_reference: str | None = None
    def __post_init__(self) -> None:
        if not isinstance(self.outcome, GovernanceOutcome): object.__setattr__(self, "outcome", GovernanceOutcome(self.outcome))
        for n in ("reason", "request_reference", "decision_reference"):
            object.__setattr__(self, n, _text(getattr(self, n), n))
        if self.evidence_reference is not None: object.__setattr__(self, "evidence_reference", _text(self.evidence_reference, "evidence_reference"))
        _safe((self.reason, self.request_reference, self.decision_reference, self.evidence_reference or ""))
    def canonical_bytes(self) -> bytes: return json.dumps(self.__dict__ if False else {"decision_reference": self.decision_reference, "evidence_reference": self.evidence_reference, "outcome": self.outcome.value, "reason": self.reason, "request_reference": self.request_reference}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def evaluate_request(
    request: ValidationExecutionRequest,
    *,
    approved_plan: bool,
    evidence_available: bool,
    authorized: bool,
    granted_capabilities: tuple[str, ...] = (),
    digest_valid: bool | None = None,
    request_reference: str = "request",
    decision_reference: str = "decision",
    evidence_reference: str | None = None,
) -> GovernanceDecision:
    if not isinstance(request, ValidationExecutionRequest): raise GovernanceError("invalid request")
    if digest_valid is False: outcome, reason = GovernanceOutcome.DENIED, "DIGEST_MISMATCH"
    elif not approved_plan or not authorized: outcome, reason = GovernanceOutcome.DENIED, "AUTHORIZATION_DENIED"
    elif not evidence_available: outcome, reason = GovernanceOutcome.BLOCKED, "EVIDENCE_UNAVAILABLE"
    elif not set(request.required_capabilities).issubset(set(granted_capabilities)): outcome, reason = GovernanceOutcome.DENIED, "CAPABILITY_MISMATCH"
    else: outcome, reason = GovernanceOutcome.ALLOWED, "APPROVED"
    return GovernanceDecision(outcome, reason, request_reference, decision_reference, evidence_reference)
