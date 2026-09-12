import json

import pytest

from app.services.evidence_validation import (
    EvidenceOutcome,
    EvidenceProvenance,
    compare_shadow,
    decide_evidence,
)
from app.services.rag import GroundingState, RetrievedChunk, SourceChunk


def chunk(source: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(SourceChunk(text="شاهد آموزشی", source_id=source), score)


def provenance() -> EvidenceProvenance:
    return EvidenceProvenance(
        source_identity="book-1",
        content_digest="sha256:abc",
        source_version="v1",
        index_generation="idx-1",
        scope="public",
        normalization_version="fa-nfc-zwnj-v1",
        trace_id="trace-1",
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"chunks": [], "trace_id": "t"}, EvidenceOutcome.ABSTAIN),
        ({"chunks": [chunk("noise")], "trace_id": "t"}, EvidenceOutcome.REJECT),
        ({"chunks": [chunk("book")], "accept": True, "trace_id": "t"}, EvidenceOutcome.ACCEPT),
        ({"chunks": [chunk("a"), chunk("b")], "conflict": True, "trace_id": "t"}, EvidenceOutcome.CONFLICT),
        ({"chunks": [], "retrieval_failure": True, "trace_id": "t"}, EvidenceOutcome.RETRIEVAL_FAILURE),
    ],
)
def test_decision_outcomes_are_closed(kwargs, expected) -> None:
    assert decide_evidence(**kwargs).outcome is expected


def test_rejected_chunks_never_appear_as_accepted() -> None:
    decision = decide_evidence([chunk("noise")], trace_id="t")
    assert decision.accepted_source_ids == ()
    assert decision.rejected_source_ids == ("noise",)


def test_provenance_and_canonical_serialization_are_deterministic() -> None:
    decision = decide_evidence(
        [chunk("book")], accept=True, trace_id="t", provenance=[provenance()]
    )
    first = decision.to_canonical_json()
    second = decision.to_canonical_json()
    assert first == second
    payload = json.loads(first)
    assert payload["provenance"][0]["normalization_version"] == "fa-nfc-zwnj-v1"
    assert payload["outcome"] == "ACCEPT"


def test_missing_provenance_fields_fail_closed() -> None:
    with pytest.raises(ValueError):
        EvidenceProvenance("", "digest", "v1", "idx", "public", "norm", "trace")


def test_conflict_is_separate_from_abstention() -> None:
    conflict = decide_evidence([chunk("a"), chunk("b")], conflict=True, trace_id="t")
    empty = decide_evidence([], trace_id="t")
    assert conflict.outcome is EvidenceOutcome.CONFLICT
    assert empty.outcome is EvidenceOutcome.ABSTAIN


def test_score_bounds_fail_closed() -> None:
    with pytest.raises(ValueError):
        decide_evidence([chunk("bad", 1.2)], trace_id="t")


def test_shadow_compare_is_sanitized_and_does_not_change_current_state() -> None:
    decision = decide_evidence([chunk("noise")], trace_id="trace-1")
    comparison = compare_shadow(
        case_id="q-noise",
        current_state=GroundingState.SUFFICIENT_EVIDENCE,
        decision=decision,
        provenance_complete=True,
    )
    assert comparison.current_state == "SUFFICIENT_EVIDENCE"
    assert comparison.shadow_outcome is EvidenceOutcome.REJECT
    assert comparison.disagreement_category == "CURRENT_ACCEPTS_SHADOW_REJECTS"
    assert "prompt" not in comparison.to_canonical_json()


def test_shadow_compare_preserves_conflict_and_provenance_mismatch() -> None:
    decision = decide_evidence([chunk("a"), chunk("b")], conflict=True, trace_id="trace-2")
    comparison = compare_shadow(
        case_id="q-conflict",
        current_state=GroundingState.SUFFICIENT_EVIDENCE,
        decision=decision,
        provenance_complete=True,
    )
    assert comparison.disagreement_category == "CURRENT_ACCEPTS_SHADOW_CONFLICT"
    mismatch = compare_shadow(
        case_id="q-mismatch",
        current_state=GroundingState.SUFFICIENT_EVIDENCE,
        decision=decision,
        provenance_complete=False,
    )
    assert mismatch.disagreement_category == "PROVENANCE_MISMATCH"
