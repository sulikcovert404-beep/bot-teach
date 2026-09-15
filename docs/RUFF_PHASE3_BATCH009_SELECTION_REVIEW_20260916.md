# Ruff Phase 3 Batch 009 — Selection Review

## Candidate
- File: `tests/test_bale_runtime.py`
- Size: 13 lines; one safe I001 import-order finding.
- Inventory: I001=1; B008=0; BLE001=0; DTZ003=0; F811=0; F841=0.

## Risk classification
LOW. Test-only module at the Bale runtime boundary. Proposed change is limited to import ordering/blank-line normalization; runtime behavior, provider contract, assertions, and fixtures remain unchanged.

## Why selected
Small focused test with exactly one I001 finding and no behavior-oriented Ruff findings. The blast radius is limited to its import block, with a directly corresponding focused test.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `python -m py_compile tests/test_bale_runtime.py`.
3. Run `pytest -q tests/test_bale_runtime.py`.
4. `git diff --check`, secret scan, and import-only diff review.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, production, or recovery action is authorized yet.

## Gate request
Approve or reject implementation of I001-only import normalization in `tests/test_bale_runtime.py`.
