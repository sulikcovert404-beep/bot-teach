import pytest

from app.services.runtime_activation_control_plane import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def ref(i="r", s=ReferenceStatus.VALID): return ReferenceToken(i, "sha256:" + i, s)
def plane(**kw):
    d = dict(control_plane_id="cp1", activation_decision_reference=ref("d"), activation_review_reference=ref("r"), readiness_package_reference=ref("p"), governance_freeze_reference=ref("g"), baseline_manifest_reference=ref("b"), change_control_reference=ref("c"), trace_reference=ref("t"))
    d.update(kw); return RuntimeActivationControlPlane(**d)
def test_ready_is_deterministic_and_non_executable():
    c = plane(); assert evaluate_runtime_activation_control_plane(c) is ControlPlaneOutcome.CONTROL_READY
    assert c.canonical_bytes() == plane().canonical_bytes(); assert c.payload()["executable"] is False
def test_warning_blocked_not_ready_unknown():
    assert evaluate_runtime_activation_control_plane(plane(control_findings=({"message": "هشدار"},))) is ControlPlaneOutcome.CONTROL_READY_WITH_WARNINGS
    assert evaluate_runtime_activation_control_plane(plane(governance_freeze_reference=ref("g", ReferenceStatus.BLOCKED))) is ControlPlaneOutcome.CONTROL_BLOCKED
    assert evaluate_runtime_activation_control_plane(plane(activation_review_reference=ref("r", ReferenceStatus.INVALID))) is ControlPlaneOutcome.CONTROL_NOT_READY
    assert evaluate_runtime_activation_control_plane(plane(readiness_package_reference=ref("p", ReferenceStatus.REQUIRES_REVIEW))) is ControlPlaneOutcome.UNKNOWN
def test_validation_rejects_tamper_secret_and_missing_trace():
    with pytest.raises(ValueError): plane(control_digest="sha256:bad")
    with pytest.raises(ValueError): plane(control_findings=({"token": "secret"},))
    with pytest.raises(ValueError): plane(trace_reference=None)
