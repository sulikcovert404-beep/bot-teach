# Ruff Phase 3 Batch 035 Selection Review — 2026-09-16

## Candidate
`tests/test_contract_version_transition.py`

## Inventory
- I001: 1 fixable finding (line 1 import block)
- B008: 0
- BLE001: 0
- DTZ003: 0
- F811: 0
- F841: 0

## Classification
LOW RISK. Test-only, contract-focused file. Proposed change is import ordering/blank-line normalization only; no runtime source behavior is touched.

## Focused tests
Five tests collected:
- `test_record_is_immutable_and_digest_bound`
- `test_compatibility_and_decision`
- `test_bad_digest_and_secrets`
- `test_graph_cycle_and_broken_parent`
- `test_persian_unicode_safety`

## Validation plan after approval
Run Ruff I001 fix, py_compile, focused pytest (5), targeted Ruff I001/B008/BLE001/DTZ003/F811/F841, git diff --check, secret scan, and diff scope review.

Production: NONE
Recovery: SAFE HOLD
No source edit before Commander gate.
