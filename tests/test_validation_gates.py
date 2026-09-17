from app.services.validation_gates import (
    GateReasonCode,
    GateResult,
    GateStatus,
    run_validation_gates,
)


def gate(name, status=GateStatus.PASSED, code=GateReasonCode.OK, message="ok"):
    class G:
        gate_name = name
        def evaluate(self, context):
            return GateResult(name, status, code, message)
    return G()


def test_all_pass_and_order():
    report = run_validation_gates({}, [gate(n) for n in reversed(("configuration_valid", "metadata_valid", "authorization_valid", "lifecycle_valid", "policy_valid", "digest_valid"))])
    assert report.valid
    assert [r.gate_name for r in report.results] == ["configuration_valid", "metadata_valid", "authorization_valid", "lifecycle_valid", "policy_valid", "digest_valid"]


def test_first_failure_stops_and_preserves_evidence():
    report = run_validation_gates({}, [gate("configuration_valid"), gate("metadata_valid", GateStatus.FAILED, GateReasonCode.GATE_FAILED, "رد نامعتبر‌است"), gate("authorization_valid")])
    assert not report.valid and report.stopped_at == "metadata_valid"
    assert len(report.results) == 2
    assert "\u200c" in report.results[1].safe_message


def test_missing_gate_is_blocked():
    report = run_validation_gates({}, [gate("configuration_valid")])
    assert report.results[-1].status is GateStatus.BLOCKED
    assert report.stopped_at == "metadata_valid"


def test_unknown_gate_fails_closed():
    report = run_validation_gates({}, [gate("nope")])
    assert report.results[0].status is GateStatus.BLOCKED
    assert report.results[0].reason_code is GateReasonCode.INVALID_GATE


def test_skipped_is_only_valid_when_explicit():
    report = run_validation_gates({}, [gate(n) for n in ("configuration_valid", "metadata_valid", "authorization_valid", "lifecycle_valid", "policy_valid", "digest_valid")[:-1]] + [gate("digest_valid", GateStatus.SKIPPED, GateReasonCode.NOT_APPLICABLE, "غیرقابل‌اعمال")])
    assert report.valid and report.results[-1].status is GateStatus.SKIPPED


def test_serialization_is_deterministic_and_nfc_safe():
    gates = [gate(n) for n in ("configuration_valid", "metadata_valid", "authorization_valid", "lifecycle_valid", "policy_valid", "digest_valid")]
    a, b = run_validation_gates({}, gates), run_validation_gates({}, gates)
    assert a.canonical_json() == b.canonical_json()
    assert "غیر" not in a.canonical_json()
