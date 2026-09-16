# Ruff Phase 3 Batch 037 — Selection Review (2026-09-16)

## Candidate
- File: `tests/test_publication_access.py`
- Scope: test-only publication/access policy contract

## Ruff inventory
- I001: 1 (blank-line normalization after import)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Focused tests
`pytest --collect-only -q tests/test_publication_access.py` collected 2 tests:
- `test_publish_requires_owner_and_same_tenant`
- `test_access_requires_membership_entitlement_and_publication`

## Risk
LOW. Pure policy tests; no runtime code or production configuration. Proposed change is import/blank-line formatting only.

## Validation plan
Ruff I001 targeted, py_compile, two focused tests, git diff check, secret scan, and diff scope review.

Production: NONE  
Recovery: SAFE HOLD

Commander approval required before source edit.
