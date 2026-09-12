from app.services.staging_activation_governance_release_readiness_archive_closure_decision_record import *
from app.services.runtime_admission_bundle import ReferenceToken,ReferenceStatus

def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(reference_id=i,digest="d-"+i,status=s)
def base(): return dict(decision_id="s1",archive_closure_review_reference=ref("f"),master_assurance_reference=ref("m"),release_certification_reference=ref("c"),final_audit_reference=ref("a"),closure_outcome=(),decision_scope={"execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_decision(StagingActivationGovernanceReleaseReadinessArchiveClosureDecisionRecordRecord(**base())) is ArchiveClosureDecisionRecordDecisionOutcome.ARCHIVE_ACCEPTED
def test_blocked(): d=base(); d["trace_reference"]=ref("t",ReferenceStatus.BLOCKED); assert evaluate_decision(StagingActivationGovernanceReleaseReadinessArchiveClosureDecisionRecordRecord(**d)) is ArchiveClosureDecisionRecordDecisionOutcome.ARCHIVE_CLOSURE_BLOCKED
def test_persian_digest(): d=base(); d["closure_outcome"]=("تأیید‌شده",); r=StagingActivationGovernanceReleaseReadinessArchiveClosureDecisionRecordRecord(**d); assert r.digest_matches()














