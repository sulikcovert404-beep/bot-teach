from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_readiness_baseline_freeze import *


def refs(status=ReferenceStatus.VALID): return [ReferenceToken(f"ref-{i}",status) for i in range(6)]
def make(**kw):
 r=refs(); return StagingActivationReadinessBaselineFreeze("freeze-1",*r, captured_state=kw.get("captured_state",{"head":"h"}), boundary_assertions=kw.get("boundary_assertions",{"execution":False}), trace_reference=ReferenceToken("trace","digest-trace",kw.get("status",ReferenceStatus.VALID)))
def test_frozen(): assert evaluate_staging_activation_readiness_baseline_freeze(make()) is StagingBaselineFreezeOutcome.STAGING_BASELINE_FROZEN
def test_blocked(): assert evaluate_staging_activation_readiness_baseline_freeze(make(status=ReferenceStatus.BLOCKED)) is StagingBaselineFreezeOutcome.STAGING_BASELINE_BLOCKED
def test_digest_and_persian():
 f=make(captured_state={"یادداشت":"می\u200cرود"}); assert f.digest_matches(); assert "sha256:" in f.freeze_digest
