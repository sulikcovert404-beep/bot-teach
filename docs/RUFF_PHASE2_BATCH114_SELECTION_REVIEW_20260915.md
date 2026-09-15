# Ruff Phase 2 Batch 114 Selection Review

Candidate: `app/services/transition_governance_package.py`

HEAD findings: 15 (`UP006`/`UP035`). Repository findings remain outside this scope.

Symbols: deprecated `typing.Mapping`/`typing.Tuple` imports and `Tuple[...]` annotations.
Remediation: combined import cleanup plus annotation modernization to built-in `tuple[...]` and `collections.abc` where applicable.

Blast radius: isolated service contract module.
Contract/runtime/introspection risk: low; changes are type syntax/import-only and must preserve serialization and behavior.
Focused tests: discover tests matching `transition_governance_package`; run if present.
Validation: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, diff check, secret scan.
Production impact: NONE
Recovery impact: SAFE HOLD

No source edit, autofix, refactor, dependency/config/workflow change, migration, deployment, or Production/Recovery action before Implementation Gate.
