import unicodedata

import pytest

from app.services.change_impact import (
    ChangeImpactRecord,
    ChangeType,
    ImpactOutcome,
    ImpactReference,
    evaluate_impact,
)


def ref(i="x"):
    return ImpactReference(i, "contract", "sha256:" + "a" * 64, "v1")

def test_no_impact_requires_warrant_and_digest_is_deterministic():
    r = ChangeImpactRecord("c1", ChangeType.CONTRACT_CHANGE, outcome=ImpactOutcome.NO_IMPACT, rationale="تغییر بی‌اثر", warrant="scope-proof")
    assert r.verify_digest() and r.canonical_bytes() == r.canonical_bytes()

def test_outcomes_and_incomplete_graph_fail_closed():
    assert evaluate_impact(complete_graph=True, outcome=ImpactOutcome.REQUIRES_REVALIDATION) is ImpactOutcome.REQUIRES_REVALIDATION
    assert evaluate_impact(complete_graph=False, outcome=ImpactOutcome.NO_IMPACT, warrant="x") is ImpactOutcome.BLOCKED
    assert evaluate_impact(complete_graph=True, outcome=ImpactOutcome.NO_IMPACT) is ImpactOutcome.UNKNOWN

def test_linkage_and_immutability():
    r = ChangeImpactRecord("c2", ChangeType.EVIDENCE_CHANGE, dependency_changes=(ref(),), trace_reference=ref("trace"), outcome=ImpactOutcome.UNKNOWN)
    with pytest.raises(Exception): r.change_id = "x"
    assert r.dependency_changes[0].target_id == "x" and r.trace_reference.target_id == "trace"

def test_digest_mismatch_and_secret_rejected():
    with pytest.raises(ValueError): ChangeImpactRecord("c", ChangeType.POLICY_CHANGE, digest="sha256:" + "b" * 64)
    with pytest.raises(ValueError): ChangeImpactRecord("c", ChangeType.POLICY_CHANGE, rationale="api_key=secret")

def test_persian_nfc_zwnj_round_trip():
    text = "می\u200cرود"
    r = ChangeImpactRecord("c3", ChangeType.CONFIGURATION_CHANGE, rationale=unicodedata.normalize("NFD", text), outcome=ImpactOutcome.UNKNOWN)
    assert "\u200c" in r.rationale and unicodedata.is_normalized("NFC", r.rationale)
