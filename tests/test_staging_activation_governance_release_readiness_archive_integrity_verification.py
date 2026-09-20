from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_archive_integrity_verification import *


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return {"verification_id": "s1","archive_manifest_reference": ref("f"),"master_assurance_reference": ref("m"),"release_certification_reference": ref("c"),"final_audit_reference": ref("a"),"verified_references": ("governance",),"boundary_assertions": {"execution":False},"trace_reference": ref("t")}
def test_accept(): assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveIntegrityRecord(**base())) is ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveIntegrityRecord(**d)) is ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_BLOCKED
def test_persian_digest(): d=base(); d["verified_references"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveIntegrityRecord(**d); assert r.digest_matches()




