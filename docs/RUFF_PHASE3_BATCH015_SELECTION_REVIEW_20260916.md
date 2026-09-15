# Ruff Phase 3 Batch 015 — Selection Review

Candidate: tests/test_admin_authorization.py

Ruff inventory:
- I001 = 1 (fixable)
- B008 = 0
- BLE001 = 0
- DTZ003 = 0
- F811 = 0
- F841 = 0

Risk: LOW for the proposed change: test-only authorization contract, import ordering only; authorization assertions and semantics remain untouched.
Focused tests: pytest -q tests/test_admin_authorization.py (5 tests collected).

Validation plan: Ruff I001, py_compile, focused pytest, git diff --check, secret scan, import-only diff review.
Production/Recovery impact: NONE / SAFE HOLD.
Pre-gate: no source edit/autofix/refactor/production action until approval.
