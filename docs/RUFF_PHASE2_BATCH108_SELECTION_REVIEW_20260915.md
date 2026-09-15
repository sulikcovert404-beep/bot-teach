# Ruff Phase 2 Batch 108 Selection Review — 2026-09-15

Candidate: `app/services/third_development_wave_execution_scope_definition.py`
HEAD findings: 16 UP006/UP035 (Ruff JSON).
Symbols: deprecated typing collection imports and annotations; audit exact symbols before implementation.
Remediation: import cleanup plus annotation modernization; selection only, no source edit authorized yet.
Blast radius: localized immutable development-wave execution scope contract.
Risks: verify field shape, defaults, ordering, serialization, runtime and introspection compatibility.
Focused tests: discover before implementation.
Validation proposed: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, scope/diff check, secret scan.
Production impact: NONE
Recovery impact: SAFE HOLD

Status: Selection review only; no source change, autofix, refactor, dependency/config/workflow change, migration, deployment, or production/recovery action.
