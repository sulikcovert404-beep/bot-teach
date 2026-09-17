from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.staging_activation_governance_final_audit import *


def make(status=ReferenceStatus.VALID,**kw):
 r=[ReferenceToken(f"r{i}",f"d{i}",status) for i in range(6)]
 return StagingActivationGovernanceFinalAudit("a1",*r,audit_findings=kw.get("findings",()),integrity_summary=kw.get("integrity",{"digest":True}),boundary_assertions=kw.get("boundary",{"execution":False}),trace_reference=ReferenceToken("trace","dt"))
def test_passed(): assert evaluate_staging_activation_governance_final_audit(make()) is FinalAuditOutcome.AUDIT_PASSED
def test_blocked(): assert evaluate_staging_activation_governance_final_audit(make(ReferenceStatus.BLOCKED)) is FinalAuditOutcome.AUDIT_BLOCKED
def test_failed_persian():
 a=make(findings=("اختلاف",)); assert evaluate_staging_activation_governance_final_audit(a) is FinalAuditOutcome.AUDIT_FAILED; assert a.digest_matches()
