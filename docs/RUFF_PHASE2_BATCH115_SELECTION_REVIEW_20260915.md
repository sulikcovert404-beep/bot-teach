# Ruff Phase 2 Batch 115 Selection Review

Candidate: `app/services/next_capability_prioritization.py`

HEAD findings: 14 (`UP006`/`UP035`) according to current Ruff JSON. This is the smallest deterministic candidate after excluding already-closed batches; other files remain outside scope.

Symbols: deprecated typing collection imports and `Tuple[...]` annotations (exact locations recorded by Ruff).
Remediation: combined import cleanup and annotation modernization to built-in generics; no runtime logic changes.

Blast radius: isolated service prioritization contract module.
Contract/runtime/introspection risks: low but must be verified; preserve field ordering, defaults, serialization, and behavior.
Focused tests: discover tests matching `next_capability_prioritization`; execute if present after authorization.
Validation plan: targeted Ruff UP006/UP035, py_compile, typing.get_type_hints, focused pytest, git diff --check, and secret scan.
Production impact: NONE
Recovery impact: SAFE HOLD

Until Implementation Gate: no source edit, autofix, refactor, dependency/config/workflow change, migration, deployment, Production, or Recovery action.
