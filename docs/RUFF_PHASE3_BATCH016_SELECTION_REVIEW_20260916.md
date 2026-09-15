# Ruff Phase 3 Batch 016 — Selection Review

Candidate: tests/test_admin_scope.py
Ruff inventory: I001=1 (fixable); B008=0; BLE001=0; DTZ003=0; F811=0; F841=0.
Risk: LOW. Test-only admin scope contract; import ordering/blank-line normalization only. Scope and assertions unchanged.
Focused tests: pytest -q tests/test_admin_scope.py (4 tests collected).
Validation: Ruff I001, py_compile, focused pytest, git diff --check, secret scan, import-only diff review.
Production/Recovery impact: NONE / SAFE HOLD.
Pre-gate: no source edit, autofix, refactor, or production action until approval.
