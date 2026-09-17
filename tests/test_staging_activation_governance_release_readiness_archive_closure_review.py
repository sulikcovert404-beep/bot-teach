from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_archive_closure_review import *


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(review_id="s1",archive_final_package_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),closure_findings=(),dependency_summary={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveClosureRecord(**base())) is ArchiveClosureOutcome.ARCHIVE_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveClosureRecord(**d)) is ArchiveClosureOutcome.ARCHIVE_BLOCKED
def test_persian_digest(): d=base(); d["closure_findings"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveClosureRecord(**d); assert r.digest_matches()











