from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_entry_governance_consolidation import (
    ConsolidationOutcome,
    RuntimeEntryGovernanceConsolidation,
    evaluate_runtime_entry_governance_consolidation,
)


def ref(name="x", status=ReferenceStatus.VALID):
    return ReferenceToken(name, "sha256:" + name, status)


def make(**changes):
    identifier = changes.pop("consolidation_id", "c1")
    data = {name: ref(name) for name in (
        "governance_freeze_reference", "baseline_manifest_reference", "change_control_reference",
        "consistency_audit_reference", "preparation_review_reference", "preparation_snapshot_reference",
        "preparation_handoff_reference", "readiness_reconciliation_reference",
        "runtime_entry_decision_reference", "trace_reference")}
    data.update(changes)
    return RuntimeEntryGovernanceConsolidation(identifier, **data)


def test_outcomes():
    assert evaluate_runtime_entry_governance_consolidation(make()) is ConsolidationOutcome.CONSOLIDATED
    assert evaluate_runtime_entry_governance_consolidation(make(validation_findings=({"code": "DRIFT"},))) is ConsolidationOutcome.CONSOLIDATED_WITH_WARNINGS
    assert evaluate_runtime_entry_governance_consolidation(make(baseline_manifest_reference=ref("b", ReferenceStatus.BLOCKED))) is ConsolidationOutcome.BLOCKED
    assert evaluate_runtime_entry_governance_consolidation(make(change_control_reference=ref("c", ReferenceStatus.REQUIRES_REVIEW))) is ConsolidationOutcome.UNKNOWN
    assert evaluate_runtime_entry_governance_consolidation(make(change_control_reference=ref("c", ReferenceStatus.INVALID))) is ConsolidationOutcome.NOT_CONSOLIDATED


def test_digest_and_determinism_and_persian():
    a = make(consolidation_id="می‌شود")
    assert a.digest_matches() and a.canonical_bytes() == make(consolidation_id="می‌شود").canonical_bytes()
    object.__setattr__(a, "consolidation_digest", "sha256:bad")
    assert evaluate_runtime_entry_governance_consolidation(a) is ConsolidationOutcome.BLOCKED


def test_non_authoritative_schema():
    p = make().payload()
    assert p["runtime_admission"] == "PROHIBITED" and p["executable"] is False
