# Ruff Phase 3 Batch 036 — Selection Review (2026-09-16)

## Candidate
- File: `tests/test_teacher_scope.py`
- Scope: test-only, teacher class authorization contract

## Ruff inventory
- I001: 1 (fixable import ordering/blank-line normalization)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Focused tests
`pytest --collect-only -q tests/test_teacher_scope.py` collected 2 tests:
- `test_teacher_can_access_assigned_class_only`
- `test_missing_assignment_denies`

## Risk and rationale
LOW risk. The file contains only policy tests; the single finding is import formatting. No runtime application code, assertions, fixtures, or authorization semantics need to change.

## Proposed implementation
Run Ruff I001 fix only on this file, then run targeted Ruff, py_compile, focused pytest, diff check, and secret scan. No broad autofix or refactor.

## Impact
Production: NONE  
Recovery: SAFE HOLD  
No deployment, migration, configuration, or database action.

## Gate request
Commander approval required before source edit.
