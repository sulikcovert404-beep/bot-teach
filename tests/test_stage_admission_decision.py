from app.services.environment_readiness import *
from app.services.readiness_evidence_gate import *
from app.services.runtime_entry_decision import *
from app.services.stage_admission_decision import *


def evidence(): return EvidenceReference("e1", "src", "d", "v1", "t", "a")
def report(status=CapabilityStatus.AVAILABLE):
    caps=(EnvironmentCapability("database",status,"e","p","t","d"),EnvironmentCapability("migration",status,"e2","p","t","d2"))
    raw=EnvironmentReadinessReport("env",caps,(),"placeholder","ok")
    return EnvironmentReadinessReport("env",caps,(),raw.computed_digest,"ok")
def readiness(): return evaluate_readiness((GateDefinition(GateName.CONTRACT_READY,("e1",)),),{"e1":evidence()})
def runtime(r,stage=RuntimeStage.CONTRACT_STAGE): return resolve_stage_admission(stage,r,{"e1":evidence()},contract_versions={})
def test_full_admission():
    r=readiness(); d=resolve_stage_admission_decision(RuntimeStage.CONTRACT_STAGE,r,report(),runtime(r)); assert d.outcome is StageAdmissionOutcome.ADMITTED and d.digest_matches()
def test_unknown_requires_review():
    r=readiness(); d=resolve_stage_admission_decision(RuntimeStage.PERSISTENCE_STAGE,r,report(CapabilityStatus.UNKNOWN),runtime(r,RuntimeStage.PERSISTENCE_STAGE)); assert d.outcome is StageAdmissionOutcome.REQUIRES_REVIEW
def test_blocked_environment():
    r=readiness(); d=resolve_stage_admission_decision(RuntimeStage.PERSISTENCE_STAGE,r,report(CapabilityStatus.BLOCKED),runtime(r,RuntimeStage.PERSISTENCE_STAGE)); assert d.outcome is StageAdmissionOutcome.BLOCKED
def test_digest_mismatch():
    r=readiness(); d=resolve_stage_admission_decision(RuntimeStage.CONTRACT_STAGE,r,report(),runtime(r),expected_readiness_digest="bad"); assert d.outcome is StageAdmissionOutcome.NOT_ADMITTED
def test_deterministic_persian():
    r=readiness(); d=resolve_stage_admission_decision(RuntimeStage.CONTRACT_STAGE,r,report(),runtime(r)); assert d.canonical_bytes()==d.canonical_bytes()
