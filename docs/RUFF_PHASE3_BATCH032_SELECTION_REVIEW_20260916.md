# Ruff Phase 3 Batch 032 Selection Review — 2026-09-16

## Candidate
- File: `tests/test_content_integration_validation.py`
- Type: test-only contract/validation review
- Proposed scope: import ordering (`I001`) only

## Ruff inventory
Targeted rules `I001,B008,BLE001,DTZ003,F811,F841`:
- I001: 1 (fixable)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Risk
LOW. Only import normalization is proposed; validation semantics, assertions, fixtures and contracts remain unchanged.

## Focused tests
Three tests collected: `test_validated_and_immutable`, `test_warning_and_failure`, `test_guards_block`.

## Validation plan
Apply only Ruff I001 fix; run targeted Ruff, py_compile, three focused pytest tests, git diff --check, secret scan and diff scope review.

## Impact
Production: NONE
Recovery: SAFE HOLD
No source edit/autofix/refactor/production action before approval.

## Gate request
Approve or reject implementation for this candidate and scope.
