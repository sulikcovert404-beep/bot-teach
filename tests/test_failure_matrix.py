from app.services.failure_matrix import *
import unicodedata

def ctx(source, category, reason="ERR_TEST"):
    return FailureContext(source,"runtime","publish",category,reason)

def test_canonical_scenarios_and_ambiguous_reconcile():
    assert resolve_failure(ctx(FailureSource.VALIDATION,FailureCategory.PERMANENT)).recovery_action is RecoveryAction.ABORT_NO_OP
    d=resolve_failure(ctx(FailureSource.AMBIGUOUS,FailureCategory.AMBIGUOUS)); assert d.recovery_action is RecoveryAction.RECONCILE
    assert d.job_impact is JobImpact.AMBIGUOUS

def test_policy_and_cancellation():
    assert resolve_failure(ctx(FailureSource.POLICY,FailureCategory.POLICY_BLOCKED)).recovery_action is RecoveryAction.ESCALATE
    assert resolve_failure(ctx(FailureSource.CANCELLATION,FailureCategory.PERMANENT)).job_impact is JobImpact.CANCELLED

def test_deterministic_and_persian_round_trip():
    reason="خطای پیش‌نویس"; c=ctx(FailureSource.RUNTIME,FailureCategory.TRANSIENT,reason)
    d=resolve_failure(c); assert d.canonical_json()==resolve_failure(c).canonical_json(); assert "پیش‌نویس" in d.canonical_json()
    assert unicodedata.normalize("NFC",reason)==reason

def test_transient_mapping():
    assert resolve_failure(ctx(FailureSource.RUNTIME,FailureCategory.TRANSIENT)).recovery_action is RecoveryAction.RETRY
