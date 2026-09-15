# Ruff Phase 3 Batch 013 — Selection Review

Candidate: tests/test_benchmark_design_prep.py

Ruff inventory:
- I001 = 1 (fixable)
- B008 = 0
- BLE001 = 0
- DTZ003 = 0
- F811 = 0
- F841 = 0

Risk: LOW. Test-only benchmark design contract; proposed change is import ordering/blank-line normalization only.
Focused tests: pytest -q tests/test_benchmark_design_prep.py (4 tests collected).

Validation plan:
- Ruff I001 only and verify zero findings
- py_compile
- focused pytest
- git diff --check
- secret scan
- diff review restricted to imports/blank lines

Production/Recovery impact: NONE / SAFE HOLD

Pre-gate constraints: No source edit, no autofix, no refactor, no production action until Commander approval.
