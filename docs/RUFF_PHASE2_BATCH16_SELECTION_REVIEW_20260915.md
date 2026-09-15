# Ruff Phase 2 Batch 16 Selection Review — 2026-09-15

## Candidate
`app/services/knowledge_runtime.py`

Inventory shows one UP035 finding (`Iterable` imported from `typing`). The module is a pure scoped retrieval qualification helper with direct tests in `tests/test_knowledge_runtime.py`.

## Assessment
Small import-only diff with medium contract/runtime risk because scope-before-ranking, approval/publication/vector eligibility, Persian normalization, and citation evidence behavior must remain unchanged.

## Proposed scope (pending Commander gate)
Modernize only the `Iterable` import to `collections.abc`. Preserve tenant/classroom/grade filtering before ranking, lifecycle eligibility, normalization, and evidence output. No routes, migrations, deployment, provider, config, dependency, workflow, or production changes.

## Required validation after approval
Targeted Ruff UP006/UP035, py_compile, knowledge-runtime tests, scope-before-ranking and lifecycle behavior review, Persian normalization/citation review, secret scan, and static typing if available.
