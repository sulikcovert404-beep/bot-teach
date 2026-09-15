# Ruff Phase 2 Batch 64 Selection Review — 2026-09-15

Candidate: `app/services/architecture_program_closure_package.py`

Findings: 1 UP035 (`typing.Tuple` import) and 7 UP006 tuple annotation findings (lines 17–23); 8 total. Unlike prior batches, this requires annotation rewrites, not import-only cleanup.

Risk assessment: service-level contract/data-shape module. Tuple annotations may affect static typing and compatibility; no runtime behavior is expected to change, but signatures and serialized shape assumptions require explicit review. This is not safe for automatic autofix without a dedicated implementation gate.

Proposed scope if approved: replace deprecated Tuple annotations with built-in `tuple[...]` syntax and remove the now-unused import, preserving all values, ordering, APIs, and runtime logic. No unrelated modernization.

Validation after approval: targeted Ruff, py_compile, type/static checks if available, focused tests, public API/contract diff review, git diff --check, and secret scan.

Implementation: NOT STARTED; awaiting Commander decision.
Production impact: NONE. Recovery: SAFE HOLD. No deployment, migration, config, workflow, dependency, or runtime action.
