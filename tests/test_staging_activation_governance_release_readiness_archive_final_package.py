from app.services.staging_activation_governance_release_readiness_archive_final_package import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(package_id="s1",archive_certification_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),archive_scope=(),historical_position={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveFinalPackageRecord(**base())) is ArchiveFinalPackageOutcome.ARCHIVE_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_certification(StagingActivationGovernanceReleaseReadinessArchiveFinalPackageRecord(**d)) is ArchiveFinalPackageOutcome.ARCHIVE_PACKAGE_BLOCKED
def test_persian_digest(): d=base(); d["archive_scope"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveFinalPackageRecord(**d); assert r.digest_matches()










