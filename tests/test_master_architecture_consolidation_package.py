from app.services.master_architecture_consolidation_package import MasterArchitectureConsolidationPackage, Outcome


def make(**kw):
    b = dict(architecture_map=("governance",), implemented_contracts=("contracts",),
              design_artifacts=("design",), prohibited_areas=("runtime",), dependency_graph=("g->r",),
              lineage_summary=("trace",), future_entry_conditions=("approval",), trace_reference="t")
    b.update(kw)
    return MasterArchitectureConsolidationPackage(**b)


def test_consolidated_and_immutable():
    p = make(); assert p.outcome() is Outcome.CONSOLIDATED
    try:
        p.trace_reference = "x"; assert False
    except AttributeError: pass


def test_blocked_without_trace():
    assert make(trace_reference="").outcome() is Outcome.BLOCKED


def test_runtime_guard_and_incomplete():
    assert make(runtime_execution=True).outcome() is Outcome.INCOMPLETE
    assert make(design_artifacts=()).outcome() is Outcome.INCOMPLETE
