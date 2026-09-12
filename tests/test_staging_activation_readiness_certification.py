from app.services.staging_activation_readiness_certification import *
from app.services.runtime_admission_bundle import ReferenceStatus,ReferenceToken
def make(status=ReferenceStatus.VALID,**kw):
 r=[ReferenceToken(f"r{i}",f"d{i}",status) for i in range(6)]
 return StagingActivationReadinessCertification("c1",*r,certification_findings=kw.get("findings",()),certification_scope=kw.get("scope",{"ready":True}),boundary_assertions=kw.get("boundary",{"execution":False}),trace_reference=ReferenceToken("trace","dt"))
def test_ready(): assert evaluate_staging_activation_readiness_certification(make()) is CertificationOutcome.CERTIFIED_READY
def test_blocked(): assert evaluate_staging_activation_readiness_certification(make(ReferenceStatus.BLOCKED)) is CertificationOutcome.CERTIFICATION_BLOCKED
def test_failed_persian():
 c=make(findings=("ایراد",)); assert evaluate_staging_activation_readiness_certification(c) is CertificationOutcome.CERTIFICATION_FAILED; assert c.digest_matches()
