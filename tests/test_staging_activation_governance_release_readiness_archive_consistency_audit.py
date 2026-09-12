from app.services.staging_activation_governance_release_readiness_archive_consistency_audit import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(audit_id="s1",archive_integrity_verification_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),consistency_findings=("governance",),boundary_assertions={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveConsistencyRecord(**base())) is ArchiveConsistencyOutcome.ARCHIVE_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveConsistencyRecord(**d)) is ArchiveConsistencyOutcome.ARCHIVE_BLOCKED
def test_persian_digest(): d=base(); d["consistency_findings"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveConsistencyRecord(**d); assert r.digest_matches()





