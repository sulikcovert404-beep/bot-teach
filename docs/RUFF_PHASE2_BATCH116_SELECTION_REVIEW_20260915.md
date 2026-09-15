# Ruff Phase 2 Batch 116 Selection Review

Candidate: `app/services/second_development_wave_execution_scope_definition.py`

HEAD findings: 15 (`UP006`/`UP035`) according to current Ruff JSON.

Symbols: deprecated typing collection imports and `Tuple[...]` annotations.
Remediation: combined import cleanup and annotation modernization to built-in generics; no runtime logic changes.

Blast radius: isolated service execution-scope contract module.
Contract/runtime/introspection risks: low; preserve contract fields, defaults, ordering, serialization, and behavior.
Focused tests: discover tests matching `second_development_wave_execution_scope_definition`; execute after authorization.
Validation plan: targeted Ruff UP006/UP035, py_compile, typing.get_type_hints, focused pytest, git diff --check, and secret scan.
Production impact: NONE
Recovery impact: SAFE HOLD

Until Implementation Gate: no source edit, autofix, refactor, dependency/config/workflow change, migration, deployment, Production, or Recovery action.
