from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_readiness_certification_bundle import *


def make(status=ReferenceStatus.VALID,**kw):
 r=[ReferenceToken(f"r{i}",f"d{i}",status) for i in range(8)]
 return StagingActivationReadinessCertificationBundle("b1",*r,bundle_findings=kw.get("findings",()),boundary_assertions=kw.get("boundary",{"execution":False}),trace_reference=ReferenceToken("trace","dt"))
def test_ready(): assert evaluate_staging_activation_readiness_certification_bundle(make()) is CertificationBundleOutcome.CERTIFICATION_BUNDLE_READY
def test_blocked(): assert evaluate_staging_activation_readiness_certification_bundle(make(ReferenceStatus.BLOCKED)) is CertificationBundleOutcome.CERTIFICATION_BUNDLE_BLOCKED
def test_not_ready_persian():
 b=make(findings=("ایراد",)); assert evaluate_staging_activation_readiness_certification_bundle(b) is CertificationBundleOutcome.CERTIFICATION_BUNDLE_NOT_READY; assert b.digest_matches()
