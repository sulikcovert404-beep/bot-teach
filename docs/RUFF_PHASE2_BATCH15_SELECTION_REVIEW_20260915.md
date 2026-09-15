# Ruff Phase 2 Batch 15 Selection Review — 2026-09-15

## Candidate
`app/services/execution_contract.py`

Inventory shows one UP035 finding (`Mapping` imported from `typing`). The module is a pure execution seam with focused coverage in `tests/test_execution_contract.py`; no adapter or runtime side effects.

## Assessment
Small import-only diff with medium contract risk because digest construction, canonical serialization, outcome transitions, and Persian NFC normalization must remain identical.

## Proposed scope (pending Commander gate)
Modernize only the `Mapping` import to `collections.abc`. Preserve request digest/canonicalization, outcome semantics, trace handling, and validation errors. No routes, migrations, deployment, provider, config, dependency, workflow, or production changes.

## Required validation after approval
Targeted Ruff UP006/UP035, py_compile, execution-contract tests, digest/serialization and outcome behavior review, secret scan, and static typing if available.
