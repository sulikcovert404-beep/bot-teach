"""Fail-open, provider-neutral shadow evidence observation.

The observer is a workspace-only sidecar.  It consumes evidence that the
normal retrieval path has already produced and never calls a provider,
retriever, database, or network service.  It is disabled by default and the
public response path does not depend on it.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from json import dumps

from app.services.evidence_validation import (
    EvidenceDecision,
    EvidenceOutcome,
    ShadowComparison,
    compare_shadow,
)
from app.services.rag import GroundingState


class SamplingReason(StrEnum):
    NORMAL = "normal"
    CRITICAL = "critical"
    FORCED = "forced"


@dataclass(frozen=True)
class ShadowObserverConfig:
    """Configuration for the sidecar; ``enabled`` intentionally defaults off."""

    enabled: bool = False
    evaluate_all: bool = True
    base_sample_rate: float = 0.01
    policy_version: str = "shadow-v1"
    observer_version: str = "observer-v1"
    normalizer_version: str = "fa-nfc-zwnj-v1"
    sampling_salt: str = "shadow-v1"
    budget_ms: int = 50

    def __post_init__(self) -> None:
        if not 0.0 <= self.base_sample_rate <= 1.0:
            raise ValueError("base_sample_rate must be between 0 and 1")
        if self.budget_ms <= 0 or self.budget_ms > 50:
            raise ValueError("observer budget must be between 1 and 50 ms")
        for value in (self.policy_version, self.observer_version, self.normalizer_version, self.sampling_salt):
            if not value.strip():
                raise ValueError("observer version and sampling metadata are required")


@dataclass(frozen=True)
class SanitizedShadowEvent:
    """Allowlisted event.  It deliberately contains no user or source text."""

    trace_id: str
    decision_version: str
    observer_version: str
    policy_version: str
    outcome: str
    reason_code: str
    disagreement_category: str
    source_ids: tuple[str, ...]
    score_summary: tuple[tuple[str, float], ...]
    score_kind: str
    retriever_identity: str
    index_generation: str
    normalizer_version: str
    artifact_hash: str
    sampling_reason: SamplingReason
    provenance_complete: bool
    latency_ms: float

    def __post_init__(self) -> None:
        required = (self.trace_id, self.decision_version, self.observer_version,
                    self.policy_version, self.reason_code, self.score_kind,
                    self.retriever_identity, self.index_generation,
                    self.normalizer_version, self.artifact_hash)
        if any(not value.strip() for value in required):
            raise ValueError("sanitized event identity fields are required")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        if any(not source.strip() for source in self.source_ids):
            raise ValueError("source ids must be opaque and non-empty")

    def to_canonical_json(self) -> str:
        return dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class ShadowCounters:
    """Counters live outside the bounded event queue so drops are observable."""

    def __init__(self) -> None:
        self.evaluated = 0
        self.retained = 0
        self.dropped_normal = 0
        self.dropped_critical = 0
        self.timeout = 0
        self.failure = 0


class BoundedShadowQueue:
    """Non-blocking queue with explicit normal/critical drop accounting."""

    def __init__(self, maxsize: int = 1024, counters: ShadowCounters | None = None) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._items: list[SanitizedShadowEvent] = []
        self._maxsize = maxsize
        self.counters = counters or ShadowCounters()

    def put_nowait(self, event: SanitizedShadowEvent, *, critical: bool) -> bool:
        if len(self._items) >= self._maxsize:
            if critical:
                self.counters.dropped_critical += 1
            else:
                self.counters.dropped_normal += 1
            return False
        self._items.append(event)
        return True

    def drain(self) -> tuple[SanitizedShadowEvent, ...]:
        items = tuple(self._items)
        self._items.clear()
        return items


def deterministic_sample(trace_id: str, *, rate: float, salt: str) -> bool:
    """Return a stable sampling decision independent of process or wall clock."""
    if not trace_id.strip() or not salt.strip():
        raise ValueError("trace_id and salt are required")
    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate must be between 0 and 1")
    if rate == 0.0:
        return False
    if rate == 1.0:
        return True
    bucket = int.from_bytes(hashlib.sha256(f"{salt}:{trace_id}".encode()).digest()[:8], "big")
    return bucket / 2**64 < rate


def _critical(comparison: ShadowComparison) -> bool:
    return comparison.disagreement_category != "AGREEMENT" or comparison.shadow_outcome in {
        EvidenceOutcome.CONFLICT,
        EvidenceOutcome.RETRIEVAL_FAILURE,
    }


def _artifact_hash(comparison: ShadowComparison, decision: EvidenceDecision, config: ShadowObserverConfig) -> str:
    payload = "|".join((comparison.to_canonical_json(), decision.to_canonical_json(), config.policy_version))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ShadowObserver:
    """Evaluate and optionally enqueue sanitized compare events.

    The method always performs the pure comparison when enabled, even when a
    normal event will not be retained.  Queue insertion is ``put_nowait`` and
    therefore cannot backpressure the current response path.
    """

    def __init__(self, config: ShadowObserverConfig | None = None, queue: BoundedShadowQueue | None = None) -> None:
        self.config = config or ShadowObserverConfig()
        self.queue = queue or BoundedShadowQueue()
        self.counters = self.queue.counters

    def observe(
        self,
        *,
        case_id: str,
        current_state: GroundingState | str,
        decision: EvidenceDecision,
        provenance_complete: bool,
        score_kind: str = "unknown",
        retriever_identity: str = "unknown",
        index_generation: str = "unknown",
        force_sample: bool = False,
    ) -> ShadowComparison | None:
        if not self.config.enabled:
            return None
        started = time.perf_counter()
        comparison = compare_shadow(
            case_id=case_id,
            current_state=current_state,
            decision=decision,
            provenance_complete=provenance_complete,
        )
        self.counters.evaluated += 1
        critical = _critical(comparison)
        sampled = force_sample or critical or deterministic_sample(
            decision.trace_id, rate=self.config.base_sample_rate, salt=self.config.sampling_salt
        )
        if not sampled:
            return comparison
        reason = SamplingReason.FORCED if force_sample else SamplingReason.CRITICAL if critical else SamplingReason.NORMAL
        event = SanitizedShadowEvent(
            trace_id=decision.trace_id,
            decision_version=decision.decision_version,
            observer_version=self.config.observer_version,
            policy_version=self.config.policy_version,
            outcome=decision.outcome.value,
            reason_code=decision.reason_code,
            disagreement_category=comparison.disagreement_category,
            source_ids=tuple(decision.accepted_source_ids + decision.rejected_source_ids),
            score_summary=decision.score_summary,
            score_kind=score_kind,
            retriever_identity=retriever_identity,
            index_generation=index_generation,
            normalizer_version=self.config.normalizer_version,
            artifact_hash=_artifact_hash(comparison, decision, self.config),
            sampling_reason=reason,
            provenance_complete=provenance_complete,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        if self.queue.put_nowait(event, critical=critical):
            self.counters.retained += 1
        return comparison

    async def observe_with_budget(self, **kwargs: object) -> ShadowComparison | None:
        """Fail-open wrapper for integration tests; never raises observer errors."""
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.observe, **kwargs), self.config.budget_ms / 1000)
        except asyncio.TimeoutError:
            self.counters.timeout += 1
            return None
        except Exception:
            self.counters.failure += 1
            return None


__all__ = [
    "BoundedShadowQueue", "SamplingReason", "SanitizedShadowEvent", "ShadowCounters",
    "ShadowObserver", "ShadowObserverConfig", "deterministic_sample",
]
