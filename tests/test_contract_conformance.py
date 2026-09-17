
from app.services.contract_conformance import *
from app.services.failure_matrix import (
    FailureCategory,
    FailureContext,
    FailureSource,
    resolve_failure,
)


def test_registry_and_vectors_are_closed_and_deterministic():
    validate_registry()
    assert canonical_json(GOLDEN_VECTORS) == canonical_json(GOLDEN_VECTORS)
    for vector in GOLDEN_VECTORS:
        assert vector["name"] and vector["decision"] and vector["execution"]


def test_unicode_vectors_preserve_nfc_and_zwnj_and_utf8():
    text = "می\u200cرود"
    assert normalize_text(text).encode("utf-8").decode("utf-8") == text
    assert "\u200c" in normalize_text(text)
    assert "\u202e" not in normalize_text(text.replace("\u202e", ""))


def test_failure_matrix_ambiguous_and_policy_blocked_are_safe():
    ambiguous = resolve_failure(FailureContext(FailureSource.AMBIGUOUS,"commit","write",FailureCategory.AMBIGUOUS,"AMBIGUOUS_EXECUTION"))
    blocked = resolve_failure(FailureContext(FailureSource.POLICY,"policy","publish",FailureCategory.POLICY_BLOCKED,"POLICY_BLOCKED"))
    assert ambiguous.recovery_action.value == "RECONCILE"
    assert blocked.recovery_action.value != "RETRY"


def test_unknown_vocabulary_fails_closed():
    try:
        assert_closed_vocabulary("UNKNOWN", ("KNOWN",))
    except ValueError:
        return
    raise AssertionError("unknown vocabulary accepted")


def test_projection_failure_does_not_change_business_outcome():
    from app.services.control_plane import Outcome, execute_control_plane
    report = execute_control_plane({"execution_id":"e","trace_id":"t","correlation_id":"c"}, decide=lambda _: Outcome.APPROVED, audit_projector=lambda _: (_ for _ in ()).throw(RuntimeError()))
    assert report.outcome is Outcome.APPROVED
    assert report.audit.error == "AUDIT_PROJECTION_FAILED"
