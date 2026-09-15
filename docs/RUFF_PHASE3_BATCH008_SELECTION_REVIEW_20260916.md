# Ruff Phase 3 Batch 008 — Selection Review

## Candidate
- File: `tests/test_bale_adapter.py`
- Focused adapter test module; one import-only I001 finding.
- Inventory: I001=1; B008=0; BLE001=0; DTZ003=0; F811=0; F841=0.

## Risk classification
LOW. The candidate is test-only and the proposed change is limited to import ordering/blank-line normalization. No provider behavior, assertions, fixtures, runtime, or configuration changes are involved.

## Why selected
Small provider-boundary test with a single I001 finding and no runtime-sensitive findings. A focused test command is available and the blast radius is limited to the test import block.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `python -m py_compile tests/test_bale_adapter.py`.
3. Run `pytest -q tests/test_bale_adapter.py`.
4. `git diff --check`, secret scan, and verify import-only diff.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, deployment, or production/recovery action is authorized at this stage.

## Gate request
Approve or reject implementation of I001-only import normalization in `tests/test_bale_adapter.py`.
