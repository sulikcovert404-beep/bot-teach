# Ruff Phase 3 Batch 024 — Selection Review (2026-09-16)

## Candidate
- File: `tests/test_baseline_change_control.py`
- Scope: test-only baseline/change-control contract.

## Ruff inventory
- Target rules: I001,B008,BLE001,DTZ003,F811,F841
- I001: 1 (fixable import ordering)
- B008: 0; BLE001: 0; DTZ003: 0; F811: 0; F841: 0

## Focused tests
- `pytest --collect-only -q tests/test_baseline_change_control.py`: 10 tests collected.

## Risk
LOW: import-only normalization in tests; no runtime or production behavior impact.

## Validation plan
Apply only I001 fix; rerun targeted Ruff rules, py_compile, focused pytest, git diff --check, scoped secret scan, and diff scope review.

## Production / Recovery
NONE; no source edit, refactor, deployment, or operational action before approval.

## Recommendation
Approve implementation for this candidate only.
