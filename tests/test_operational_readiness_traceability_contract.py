from app.services.operational_readiness_traceability_contract import (
 OperationalReadinessTraceabilityContract,
 TraceOutcome,
)


def make(**k):
 d={'trace_contract_id': 't','governance_model_reference': 'g','assessment_framework_reference': 'a','evidence_model_reference': 'e','reference_graph': {'a':'e'},'lineage_rules': ('lineage',),'trace_validation_rules': ('valid',),'integrity_constraints': ('digest',),'scope_exclusions': ('storage',),'boundary_assertions': {'trace_storage':False,'execution':False},'trace_digest': 'd'}; d.update(k); return OperationalReadinessTraceabilityContract(**d)
def test_defined(): assert make().outcome() is TraceOutcome.TRACE_CONTRACT_DEFINED
def test_blocked(): assert make(trace_contract_id='').outcome() is TraceOutcome.TRACE_CONTRACT_BLOCKED
def test_incomplete(): assert make(lineage_rules=()).outcome() is TraceOutcome.TRACE_CONTRACT_INCOMPLETE
