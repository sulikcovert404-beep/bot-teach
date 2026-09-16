from app.services.governance_chain_meta_validation_review import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(i,"d-"+i,s)
def obj(): return StagingActivationGovernanceReleaseReadinessGovernanceChainMetaValidationRecord("r",ref("f"),ref("m"),ref("c"),ref("a"),(),{"deps":"closed","execution":False},trace_reference=ref("t"))
def test_accept(): assert evaluate_snapshot(obj()) is ChainValidationOutcome.CHAIN_VALIDATED
def test_blocked():
 d=obj(); d=StagingActivationGovernanceReleaseReadinessGovernanceChainMetaValidationRecord(d.review_id,d.final_governance_snapshot_reference,d.master_assurance_reference,d.release_certification_reference,d.final_audit_reference,d.chain_nodes_summary,d.dependency_graph_summary,trace_reference=ref("t",ReferenceStatus.BLOCKED)); assert evaluate_snapshot(d) is ChainValidationOutcome.CHAIN_BLOCKED
def test_digest(): assert obj().digest_matches()



