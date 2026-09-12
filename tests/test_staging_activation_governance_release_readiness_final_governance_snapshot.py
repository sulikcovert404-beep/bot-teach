from app.services.staging_activation_governance_release_readiness_final_governance_snapshot import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(snapshot_id="s1",archive_closure_decision_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),snapshot_position=(),snapshot_summary={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_snapshot(StagingActivationGovernanceReleaseReadinessFinalGovernanceSnapshotRecord(**base())) is FinalSnapshotOutcome.FINAL_SNAPSHOT_CONFIRMED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_snapshot(StagingActivationGovernanceReleaseReadinessFinalGovernanceSnapshotRecord(**d)) is FinalSnapshotOutcome.FINAL_SNAPSHOT_BLOCKED
def test_persian_digest(): d=base(); d["snapshot_position"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessFinalGovernanceSnapshotRecord(**d); assert r.digest_matches()

















