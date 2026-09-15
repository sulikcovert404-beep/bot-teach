# Ruff Phase 3 Batch 004 — Selection Review

## Candidate
- File: `app/core/client_contract.py`
- Size: 31 lines; one safe I001 import-order finding.
- Full file inventory: I001=1; B008=0, BLE001=0, DTZ003=0, F811=0, F841=0.

## Risk classification
LOW. This module defines shared immutable client/session data contracts. The proposed change is restricted to standard-library import ordering; no fields, defaults, validation, or runtime behavior change.

## Why selected
Small provider-neutral contract module with a single I001 finding, no runtime-sensitive Ruff findings, narrow blast radius, and focused coverage in `tests/test_client_contract.py`.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `py_compile app/core/client_contract.py`.
3. Run `tests/test_client_contract.py`.
4. Run `git diff --check`, secret scan, and verify import-only diff.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, deployment, or production/recovery action is authorized at this stage.

## Gate request
Approve or reject implementation of I001-only import normalization in `app/core/client_contract.py`.
