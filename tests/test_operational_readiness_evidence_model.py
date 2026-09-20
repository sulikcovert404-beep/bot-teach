from app.services.operational_readiness_evidence_model import (
 EvidenceOutcome,
 OperationalReadinessEvidenceModel,
)


def make(**k):
 d={'evidence_model_id': 'e','governance_model_reference': 'g','evidence_categories': ('validation',),'required_evidence_rules': {'validation':'required'},'ownership_rules': {'validation':'owner'},'trace_requirements': ('trace',),'validation_constraints': ('digest',),'scope_exclusions': ('storage',),'boundary_assertions': {'evidence_collection':False,'evidence_storage':False},'trace_reference': 't','evidence_digest': 'd'}; d.update(k); return OperationalReadinessEvidenceModel(**d)
def test_defined(): assert make().outcome() is EvidenceOutcome.EVIDENCE_MODEL_DEFINED
def test_blocked(): assert make(evidence_digest='').outcome() is EvidenceOutcome.EVIDENCE_MODEL_BLOCKED
def test_incomplete(): assert make(ownership_rules={}).outcome() is EvidenceOutcome.EVIDENCE_MODEL_INCOMPLETE
