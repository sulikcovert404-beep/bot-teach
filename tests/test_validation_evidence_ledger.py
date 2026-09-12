from app.services.validation_evidence_ledger import *


def make(status=EvidenceStatus.ACCEPTED, **kw):
    base = dict(evidence_id="ev-1", validation_id="val-1", plan_version="v1", result_status=status, artifact_reference="artifact-1", digest="0"*64, timestamp_reference="2026-01-01T00:00:00Z", source_type="test", validity_period="2026-01-02T00:00:00Z")
    base.update(kw)
    record = ValidationEvidenceRecord(**base)
    return ValidationEvidenceRecord(**{**record.as_dict(), "digest": record.computed_digest()})


def test_statuses_and_immutability():
    for status in EvidenceStatus:
        r = make(status)
        assert r.result_status is status
    try:
        make().result_status = EvidenceStatus.REJECTED
        assert False
    except AttributeError:
        pass


def test_digest_and_deterministic_serialization():
    r = make()
    assert r.canonical_bytes() == make().canonical_bytes()
    r.verify_digest()
    bad = ValidationEvidenceRecord(**{**r.as_dict(), "digest": "f"*64})
    try:
        bad.verify_digest(); assert False
    except DigestMismatchError: pass


def test_lineage_consistency_and_cycle_rejection():
    r = make(parent_evidence_reference="ev-0")
    r.validate_lineage(known_ids=frozenset({"ev-0"}))
    try:
        make(parent_evidence_reference="ev-1").validate_lineage(); assert False
    except LineageError: pass
    try:
        make(parent_evidence_reference="missing").validate_lineage(known_ids=frozenset({"ev-0"})); assert False
    except LineageError: pass


def test_secret_like_values_rejected():
    try:
        make(artifact_reference="token=supersecretvalue"); assert False
    except SecretLikeValueError: pass


def test_persian_nfc_zwnj_rtl_round_trip():
    text = "می\u200cرود ـ فیزیک"  # ZWNJ and RTL-compatible Persian text
    r = make(artifact_reference=text)
    assert r.as_dict()["artifact_reference"] == text
    assert r.computed_digest() == make(artifact_reference=text).computed_digest()
