from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_package import *


def ref(i,s="VALID"):
    return ReferenceToken(i, "sha256:"+i, status=ReferenceStatus(s))
def make(**kw):
    names=("certification_bundle_reference","readiness_certification_reference","final_audit_reference","governance_master_package_reference","baseline_freeze_reference","freeze_assurance_reference","staging_control_package_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")
    refs={n:ref(n) for n in names}; refs.update(kw)
    return StagingActivationGovernanceReleaseReadinessPackage("p", **refs, boundary_assertions={"execution":False})
def test_ready():
    assert evaluate_release_readiness_package(make()) is ReleaseReadinessOutcome.RELEASE_READY
def test_blocked():
    assert evaluate_release_readiness_package(make(certification_bundle_reference=ref("x","BLOCKED"))) is ReleaseReadinessOutcome.RELEASE_BLOCKED
def test_persian_digest():
    assert make(release_findings=("نیم‌فاصله",)).digest_matches()
