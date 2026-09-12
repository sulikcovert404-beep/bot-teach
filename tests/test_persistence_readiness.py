import pytest

from app.services.persistence_readiness import (
    PersistenceEvidence,
    PersistenceRecord,
    PersistenceResult,
    canonical_record,
    map_persistence_result,
    readiness_status,
)


def test_result_mapping_and_unknown_rejected():
    assert map_persistence_result("stored") is PersistenceResult.STORED
    with pytest.raises(ValueError):
        map_persistence_result("other")


def test_evidence_is_fail_closed():
    assert readiness_status(PersistenceEvidence()) == "NOT_READY"
    evidence = PersistenceEvidence("m", "t", "r", "a")
    assert evidence.complete and readiness_status(evidence) == "READY"


def test_record_serialization_is_deterministic():
    record = PersistenceRecord(PersistenceResult.UNKNOWN, "1", "1", "d", "ref")
    assert canonical_record(record)["result"] == "UNKNOWN"

