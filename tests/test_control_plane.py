from app.services.control_plane import Outcome, execute_control_plane


def test_approved_and_projection_isolation():
    r = execute_control_plane(
        {"execution_id": "e", "trace_id": "t", "correlation_id": "c"},
        decide=lambda _: Outcome.APPROVED,
        audit_projector=lambda _: (_ for _ in ()).throw(RuntimeError()),
        observability_projector=lambda _: "obs-1",
    )
    assert r.outcome is Outcome.APPROVED
    assert r.audit.error == "AUDIT_PROJECTION_FAILED"
    assert r.observability.reference == "obs-1"


def test_failure_is_fail_closed_and_unicode_is_preserved():
    r = execute_control_plane({"execution_id": "e", "trace_id": "ت", "correlation_id": "می\u200cشود"}, decide=lambda _: 1 / 0)
    assert r.outcome is Outcome.INTERNAL_FAILURE
    assert "می\u200cشود" in r.canonical_json()


def test_report_serialization_is_deterministic():
    args = {"execution_id": "e", "trace_id": "t", "correlation_id": "c"}
    a = execute_control_plane(args, decide=lambda _: Outcome.BLOCKED)
    b = execute_control_plane(args, decide=lambda _: Outcome.BLOCKED)
    assert a.canonical_json() == b.canonical_json()
