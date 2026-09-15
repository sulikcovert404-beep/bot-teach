# Ruff Phase 3 Batch 031 Selection Review — 2026-09-16

## Candidate
- File: `tests/test_content_integration_readiness_review.py`
- Type: test-only contract/readiness review
- Scope: import ordering (`I001`) only

## Ruff inventory
Targeted rules: `I001,B008,BLE001,DTZ003,F811,F841`

- I001: 1 (fixable)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Risk classification
LOW. The candidate contains readiness contract tests and the proposed change is limited to import normalization. No runtime, authorization, persistence, assertion, fixture, or API behavior should change.

## Focused tests
`pytest --collect-only -q tests/test_content_integration_readiness_review.py` collected 3 tests:
- `test_ready_and_immutable`
- `test_warnings_and_deferred`
- `test_guards_block`

## Validation plan
1. Apply Ruff `I001` fix only.
2. Re-run targeted Ruff rules and require zero findings.
3. Run `python -m py_compile` on the file.
4. Run the 3 focused tests.
5. Run `git diff --check` and secret scan.
6. Review diff to confirm import-only/blank-line changes.

## Production/Recovery impact
Production: NONE
Recovery: SAFE HOLD
No source edit, autofix, refactor, deployment, migration, or operational action before Commander implementation approval.

## Gate request
Please approve or reject implementation for this single candidate and scope.
