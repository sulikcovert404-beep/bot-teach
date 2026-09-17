from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_signoff_record import *


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(signoff_id="s1",final_governance_package_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),signoff_scope=("governance",),boundary_assertions={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessSignOffRecord(**base())) is SignOffOutcome.SIGNOFF_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessSignOffRecord(**d)) is SignOffOutcome.SIGNOFF_BLOCKED
def test_persian_digest(): d=base(); d["signoff_scope"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessSignOffRecord(**d); assert r.digest_matches()


