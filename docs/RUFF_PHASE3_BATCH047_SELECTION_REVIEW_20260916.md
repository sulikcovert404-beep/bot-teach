# RUFF PHASE3 BATCH047 SELECTION REVIEW — 2026-09-16

Candidate: `tests/test_failure_matrix.py`

Inventory:
- I001: 1
- B008/BLE001/DTZ003/F811/F841: 0

Risk: LOW. Test-only failure-matrix contract; proposed change only reorders imports. Failure classification behavior, assertions, fixtures, and runtime are unchanged.

Focused tests: 4 collected (`pytest -q tests/test_failure_matrix.py`).

Validation plan after approval:
- Ruff targeted rules
- py_compile
- focused pytest (expected 4 passed)
- git diff --check
- secret scan and import-only diff review

Production impact: NONE
Recovery: SAFE HOLD

No source edit or autofix performed before Commander gate.
