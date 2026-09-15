# Ruff Phase 3 Batch 006 — Selection Review

## Candidate
- File: `app/services/publication_access.py`
- Size: 16 lines; one safe I001 import-order finding.
- Full file inventory: I001=1; B008=0, BLE001=0, DTZ003=0, F811=0, F841=0.

## Risk classification
LOW. The module contains a small provider-neutral publication/access policy contract. The proposed change is limited to import spacing/order; policy predicates and access semantics remain untouched.

## Why selected
Smallest suitable application module with a single import-only finding, no runtime-sensitive findings, narrow blast radius, and focused coverage in `tests/test_publication_access.py`.

## Focused validation plan
1. Ruff `--select I001` before/after; target zero.
2. `py_compile app/services/publication_access.py`.
3. Run `tests/test_publication_access.py`.
4. Run `git diff --check`, secret scan, and verify policy behavior plus diff are unchanged apart from imports.

## Production and recovery impact
NONE. Selection only; no source edit, autofix, refactor, dependency/config, deployment, or production/recovery action is authorized at this stage.

## Gate request
Approve or reject implementation of I001-only import normalization in `app/services/publication_access.py`.
