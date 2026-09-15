# RUFF PHASE 3 BATCH 018 SELECTION REVIEW — 2026-09-16

Candidate: `tests/test_assignment_persistence_models.py`

Ruff inventory (scoped):
- I001: 1 (fixable)
- B008/BLE001/DTZ003/F811/F841: 0

Risk: LOW. Test-only persistence contract coverage; import ordering only. No model/schema behavior change authorized.
Focused tests: 2 collected.

Validation plan: targeted Ruff I001, py_compile, focused pytest, git diff --check, scoped secret scan, and diff scope review.
Production/Recovery impact: NONE / SAFE HOLD.

Implementation remains blocked pending Commander Selection Gate approval.
