# Ruff Phase 3 Batch 007 — Selection Review

## Candidate
- File: `tests/test_gemini_adapter.py`
- Size: 8 lines; one safe I001 import-order finding.
- Full file inventory: I001=1; B008=0, BLE001=0, DTZ003=0, F811=0, F841=0.

## Risk classification
LOW. This is a focused unit test module. The proposed change only separates and orders imports; the test behavior, secret assertion, and provider contract remain unchanged.

## Why selected
Minimal test-only file with a single import-only finding, no runtime-sensitive Ruff findings, and a directly corresponding focused test.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `py_compile tests/test_gemini_adapter.py`.
3. Run `tests/test_gemini_adapter.py`.
4. Run `git diff --check`, secret scan, and verify only the import block changes.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, deployment, or production/recovery action is authorized at this stage.

## Gate request
Approve or reject implementation of I001-only import normalization in `tests/test_gemini_adapter.py`.
