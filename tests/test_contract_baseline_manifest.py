from app.services.contract_baseline_manifest import ContractBaselineManifest, BaselineOutcome, evaluate_baseline
from app.services.runtime_admission_bundle import ReferenceToken


def ref(name, status='VALID'):
    from app.services.runtime_admission_bundle import ReferenceStatus
    return ReferenceToken(name, 'd'*64, ReferenceStatus(status))


def manifest(**kw):
    base = dict(baseline_id='b1', contract_inventory=('A','B'), contract_versions={'A':'1.0','B':'1.0'}, dependency_summary={'A':('B',),'B':()}, authority_summary={'a':'A','b':'B'}, digest_summary={'A':'x','B':'y'}, closure_reference=ref('closure'), trace_reference=ref('trace'))
    base.update(kw)
    return ContractBaselineManifest(**base)


def test_frozen_and_deterministic():
    m=manifest()
    assert evaluate_baseline(m)==BaselineOutcome.FROZEN
    assert m.baseline_digest==m.compute_digest()
    assert m.canonical_bytes()==manifest(contract_inventory=('B','A')).canonical_bytes()
    assert evaluate_baseline(manifest(warnings=('deprecated contract',)))==BaselineOutcome.FROZEN_WITH_WARNINGS


def test_empty_inventory_not_frozen():
    m=manifest(contract_inventory=(), contract_versions={}, dependency_summary={}, authority_summary={}, digest_summary={})
    assert evaluate_baseline(m)==BaselineOutcome.NOT_FROZEN


def test_missing_dependency_blocked():
    assert evaluate_baseline(manifest(dependency_summary={'A':('MISSING',),'B':()}))==BaselineOutcome.BLOCKED


def test_required_contract_missing_blocked():
    assert evaluate_baseline(manifest(), required_contracts=('A','C'))==BaselineOutcome.BLOCKED


def test_digest_mismatch_not_frozen():
    m=manifest()
    object.__setattr__(m,'baseline_digest','sha256:'+'0'*64)
    assert evaluate_baseline(m)==BaselineOutcome.NOT_FROZEN


def test_incomplete_closure_not_frozen():
    from app.services.runtime_admission_bundle import ReferenceStatus
    assert evaluate_baseline(manifest(closure_reference=ref('closure','REQUIRES_REVIEW')))==BaselineOutcome.NOT_FROZEN


def test_trace_review_unknown_and_secret_rejected():
    from app.services.runtime_admission_bundle import ReferenceStatus
    assert evaluate_baseline(manifest(trace_reference=ref('trace','REQUIRES_REVIEW')))==BaselineOutcome.UNKNOWN
    try:
        manifest(baseline_id='api_key')
    except ValueError:
        pass
    else:
        raise AssertionError('secret must be rejected')
