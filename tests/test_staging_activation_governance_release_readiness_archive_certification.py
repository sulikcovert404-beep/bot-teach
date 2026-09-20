from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_archive_certification import *


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return {"certification_id": "s1","archive_consistency_audit_reference": ref("f"),"master_assurance_reference": ref("m"),"release_certification_reference": ref("c"),"final_audit_reference": ref("a"),"certification_findings": (),"boundary_assertions": {"execution":False},"trace_reference": ref("t")}
def test_accept(): assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveCertificationRecord(**base())) is ArchiveCertificationOutcome.ARCHIVE_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveCertificationRecord(**d)) is ArchiveCertificationOutcome.ARCHIVE_CERTIFICATION_BLOCKED
def test_persian_digest(): d=base(); d["certification_findings"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveCertificationRecord(**d); assert r.digest_matches()









