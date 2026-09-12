from app.services.staging_activation_governance_master_package import *
from app.services.runtime_admission_bundle import ReferenceStatus,ReferenceToken
def make(status=ReferenceStatus.VALID,**kw):
 r=[ReferenceToken(f"r{i}",f"d{i}",status) for i in range(8)]
 return StagingActivationGovernanceMasterPackage("p1",*r,master_findings=kw.get("findings",()),boundary_assertions=kw.get("boundary",{"execution":False}),trace_reference=ReferenceToken("trace","dt"))
def test_ready(): assert evaluate_staging_activation_governance_master_package(make()) is MasterPackageOutcome.MASTER_READY
def test_blocked(): assert evaluate_staging_activation_governance_master_package(make(ReferenceStatus.BLOCKED)) is MasterPackageOutcome.MASTER_BLOCKED
def test_not_ready_and_persian():
 p=make(findings=("اختلاف",)); assert evaluate_staging_activation_governance_master_package(p) is MasterPackageOutcome.MASTER_NOT_READY; assert p.digest_matches()
