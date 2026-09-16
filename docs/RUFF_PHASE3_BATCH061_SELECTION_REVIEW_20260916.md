# Ruff Phase 3 Batch 061 — Selection Review (2026-09-16)

## Candidate
- Canonical path: `tests/test_migration_roundtrip_qualification.py`
- Scope: test-only migration qualification/round-trip tests
- Risk: LOW-MEDIUM (test-only; formatting cannot alter migration behavior)

## Ruff inventory
- I001: 1 (fixable import ordering)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Focused tests
Two tests collected: `test_migration_roundtrip_0019_0018_0019_and_post_smoke`, `test_dual_parent_lineage_convergence_0009_and_0019_to_0020`.

## Validation plan
After authorization, apply only I001 normalization; rerun six-rule Ruff check, py_compile, focused pytest, git diff --check, secret scan, and diff-scope review.

## Boundaries
No migration files or runtime behavior changes; no deploy, recovery, database, or production action.
