import pytest
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus
from app.services.runtime_activation_readiness_baseline_freeze import *
def make(**kw):
 r=ReferenceToken("ref","sha256:x"); vals={n:r for n in ("governance_closure_reference","activation_control_plane_reference","activation_decision_reference","readiness_package_reference","entry_preparation_reference","baseline_reference","change_control_reference","trace_reference")}; vals["captured_state"]={"version":"v1"}; vals.update(kw); return RuntimeActivationReadinessBaselineFreeze("f1",**vals)
def test_frozen_immutable_digest():
 f=make(); assert evaluate_runtime_activation_readiness_baseline_freeze(f) is BaselineFreezeOutcome.BASELINE_FROZEN; assert f.digest_matches()
 with pytest.raises((AttributeError,TypeError)): f.freeze_id="x"
def test_precedence():
 r=ReferenceToken("ref","sha256:x",ReferenceStatus.BLOCKED); assert evaluate_runtime_activation_readiness_baseline_freeze(make(governance_closure_reference=r)) is BaselineFreezeOutcome.BASELINE_BLOCKED
 assert evaluate_runtime_activation_readiness_baseline_freeze(make(captured_state={})) is BaselineFreezeOutcome.BASELINE_NOT_FROZEN
def test_secret_and_tamper():
 with pytest.raises(ValueError): make(captured_state={"token":"x"})
 with pytest.raises(ValueError): make(freeze_digest="sha256:bad")
