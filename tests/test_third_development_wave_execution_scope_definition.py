from app.services.third_development_wave_execution_scope_definition import (
    Outcome,
    ThirdDevelopmentWaveExecutionScopeDefinition,
)


def make(**overrides):
    values = dict(capability="content", objective="manage content",
                  inputs=("content command",), outputs=("content result",),
                  expected_behavior=("deterministic",), allowed_files=("app/services/content.py",),
                  forbidden_changes=("database",), success_scenarios=("valid",),
                  error_scenarios=("invalid",), regression_scenarios=("existing",),
                  edge_cases=("empty",), new_tests=("unit",), regression_tests=("suite",),
                  out_of_scope=("deployment",), implementation_changes=("service",),
                  preserved_behavior=("existing contracts",), trace_reference="trace")
    values.update(overrides)
    return ThirdDevelopmentWaveExecutionScopeDefinition(**values)


def test_defined_and_immutable():
    scope = make()
    assert scope.outcome() is Outcome.DEFINED
    try:
        scope.objective = "x"
        assert False
    except AttributeError:
        pass


def test_missing_scope_blocks():
    assert make(outputs=()).outcome() is Outcome.BLOCKED
    assert make(trace_reference="").outcome() is Outcome.BLOCKED


def test_execution_guards_block():
    assert make(feature_execution=True).outcome() is Outcome.BLOCKED
    assert make(implementation_permission=True).outcome() is Outcome.BLOCKED
