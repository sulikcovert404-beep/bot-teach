import asyncio

from app.services.evidence_validation import EvidenceProvenance, decide_evidence
from app.services.rag import GroundingState, RetrievedChunk, SourceChunk
from app.services.shadow_observer import (
    BoundedShadowQueue,
    ShadowCounters,
    ShadowObserver,
    ShadowObserverConfig,
    deterministic_sample,
)


def _decision(trace: str = "trace-1"):
    chunk = RetrievedChunk(SourceChunk(text="نباید ذخیره شود", source_id="book:v1:p1:c1"), 0.8)
    return decide_evidence(
        [chunk], accept=True, trace_id=trace,
        provenance=[EvidenceProvenance("book", "sha256:1", "v1", "idx-1", "public", "fa-v1", trace)],
    )


def test_default_observer_is_off_and_does_not_enqueue() -> None:
    observer = ShadowObserver()
    assert observer.observe(case_id="c1", current_state=GroundingState.SUFFICIENT_EVIDENCE,
                            decision=_decision(), provenance_complete=True) is None
    assert observer.counters.evaluated == 0
    assert observer.queue.drain() == ()


def test_critical_event_is_sanitized_and_retained() -> None:
    observer = ShadowObserver(ShadowObserverConfig(enabled=True, base_sample_rate=0.0))
    observer.observe(case_id="c1", current_state=GroundingState.NO_SOURCE,
                     decision=_decision(), provenance_complete=True)
    event = observer.queue.drain()[0]
    serialized = event.__dict__ if hasattr(event, "__dict__") else str(event)
    assert "نباید ذخیره شود" not in str(serialized)
    assert event.source_ids == ("book:v1:p1:c1",)
    assert event.sampling_reason.value == "critical"


def test_sampling_is_stable() -> None:
    values = [deterministic_sample("trace-42", rate=0.25, salt="v1") for _ in range(10)]
    assert len(set(values)) == 1
    assert deterministic_sample("trace-42", rate=0.0, salt="v1") is False
    assert deterministic_sample("trace-42", rate=1.0, salt="v1") is True


def test_queue_drop_counters_are_outside_event_stream() -> None:
    counters = ShadowCounters()
    queue = BoundedShadowQueue(maxsize=1, counters=counters)
    observer = ShadowObserver(ShadowObserverConfig(enabled=True, base_sample_rate=0.0), queue)
    observer.observe(case_id="c1", current_state=GroundingState.NO_SOURCE,
                     decision=_decision("t1"), provenance_complete=True)
    observer.observe(case_id="c2", current_state=GroundingState.NO_SOURCE,
                     decision=_decision("t2"), provenance_complete=True)
    assert counters.dropped_critical == 1


def test_timeout_is_fail_open() -> None:
    observer = ShadowObserver(ShadowObserverConfig(enabled=True, budget_ms=1))
    original = observer.observe

    def slow(**kwargs):
        import time
        time.sleep(0.05)
        return original(**kwargs)

    observer.observe = slow  # type: ignore[method-assign]
    result = asyncio.run(observer.observe_with_budget(case_id="c1", current_state=GroundingState.NO_SOURCE,
                                                       decision=_decision(), provenance_complete=True))
    assert result is None
    assert observer.counters.timeout == 1


def test_event_canonical_serialization_is_stable_and_allowlisted() -> None:
    observer = ShadowObserver(ShadowObserverConfig(enabled=True, base_sample_rate=1.0))
    observer.observe(case_id="c1", current_state=GroundingState.SUFFICIENT_EVIDENCE,
                     decision=_decision("trace-fa"), provenance_complete=True,
                     score_kind="cosine", retriever_identity="retriever-v1", index_generation="idx-1")
    event = observer.queue.drain()[0]
    payload = event.to_canonical_json()
    assert payload == event.to_canonical_json()
    for forbidden in ("نباید ذخیره شود", "prompt", "response", "document"):
        assert forbidden not in payload
    assert '"score_kind":"cosine"' in payload
    assert '"trace_id":"trace-fa"' in payload


def test_kill_switch_is_producer_side() -> None:
    observer = ShadowObserver(ShadowObserverConfig(enabled=False, base_sample_rate=1.0))
    observer.observe(case_id="c1", current_state=GroundingState.NO_SOURCE,
                     decision=_decision(), provenance_complete=True)
    assert observer.counters.evaluated == 0
    assert observer.queue.drain() == ()
