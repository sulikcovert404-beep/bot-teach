from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_release_readiness_certification import *


def ref(i,s="VALID"): return ReferenceToken(i,"sha256:"+i,status=ReferenceStatus(s))
def make(**kw):
 names=("release_readiness_final_review_reference","certification_bundle_reference","final_audit_reference","baseline_freeze_reference","freeze_assurance_reference","activation_control_package_reference","activation_decision_reference","trace_reference"); d={n:ref(n) for n in names}; d.update(kw); return StagingActivationGovernanceReleaseReadinessCertification("r",**d,boundary_assertions={"execution":False})
def test_ready(): assert evaluate_release_certification(make()) is ReleaseCertificationOutcome.RELEASE_READY_CONFIRMED
def test_blocked(): assert evaluate_release_certification(make(trace_reference=ref("x","BLOCKED"))) is ReleaseCertificationOutcome.RELEASE_BLOCKED
def test_persian_digest(): assert make(certification_findings=("نیم‌فاصله",)).digest_matches()


