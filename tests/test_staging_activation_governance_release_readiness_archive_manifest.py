from app.services.staging_activation_governance_release_readiness_archive_manifest import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(manifest_id="s1",signoff_record_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),archive_scope=("governance",),boundary_assertions={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveManifestRecord(**base())) is ArchiveManifestOutcome.ARCHIVE_MANIFEST_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_signoff(StagingActivationGovernanceReleaseReadinessArchiveManifestRecord(**d)) is ArchiveManifestOutcome.ARCHIVE_MANIFEST_BLOCKED
def test_persian_digest(): d=base(); d["archive_scope"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveManifestRecord(**d); assert r.digest_matches()



