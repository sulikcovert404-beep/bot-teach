from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_baseline_freeze_assurance import *


def make(status=ReferenceStatus.VALID,**kw):
 r=[ReferenceToken(f"r{i}",f"d{i}",status) for i in range(5)]
 return StagingActivationBaselineFreezeAssurance("a1",*r,drift_findings=kw.get("drift",()),integrity_findings=kw.get("integrity",()),boundary_assertions=kw.get("boundary",{"execution":False}),trace_reference=ReferenceToken("trace","dt"))
def test_confirmed(): assert evaluate_staging_activation_baseline_freeze_assurance(make()) is FreezeAssuranceOutcome.FREEZE_ASSURANCE_CONFIRMED
def test_blocked(): assert evaluate_staging_activation_baseline_freeze_assurance(make(ReferenceStatus.BLOCKED)) is FreezeAssuranceOutcome.FREEZE_ASSURANCE_BLOCKED
def test_failed_and_persian():
 a=make(drift=("اختلاف",)); assert evaluate_staging_activation_baseline_freeze_assurance(a) is FreezeAssuranceOutcome.FREEZE_ASSURANCE_FAILED; assert a.digest_matches()
