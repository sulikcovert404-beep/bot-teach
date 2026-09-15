# Ruff Phase 3 Batch 034 Selection Review — 2026-09-16

Candidate: `tests/test_contract_conformance.py` (test-only contract conformance)

Ruff targeted (`I001,B008,BLE001,DTZ003,F811,F841`): I001=1 (fixable); B008/BLE001/DTZ003/F811/F841=0.

Risk: LOW. Proposed import ordering normalization only; no contract behavior, Unicode vectors, failure matrix, assertions, fixtures, or serialization changes.

Focused tests collected: 5 (`test_registry_and_vectors_are_closed_and_deterministic`, `test_unicode_vectors_preserve_nfc_and_zwnj_and_utf8`, `test_failure_matrix_ambiguous_and_policy_blocked_are_safe`, `test_unknown_vocabulary_fails_closed`, `test_projection_failure_does_not_change_business_outcome`).

Validation plan: I001-only fix, targeted Ruff, py_compile, 5 focused tests, diff check, secret scan, import-only diff review.

Production: NONE. Recovery: SAFE HOLD.

Gate request: approve or reject implementation.
