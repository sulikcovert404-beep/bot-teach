# Ruff Phase 3 Batch 005 — Selection Review

## Candidate
- File: `app/services/audit_trail.py`
- Size: 50 lines; one safe I001 import-order finding.
- Full file inventory: I001=1; B008=0, BLE001=0, DTZ003=0, F811=0, F841=0.

## Risk classification
LOW. This is a database-free typed audit contract and observer projection. The proposed change is limited to ordering standard-library imports; event fields, serialization, timestamps, and sink behavior remain untouched.

## Why selected
Small, bounded provider-neutral/audit contract with one import-only finding, no runtime-sensitive Ruff rules, and focused coverage in `tests/test_audit_trail.py`.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `py_compile app/services/audit_trail.py`.
3. Run `tests/test_audit_trail.py`.
4. Run `git diff --check`, secret scan, and verify fields/serialization plus diff are unchanged apart from imports.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, deployment, or production/recovery action is authorized at this stage.

## Gate request
Approve or reject implementation of I001-only import normalization in `app/services/audit_trail.py`.
