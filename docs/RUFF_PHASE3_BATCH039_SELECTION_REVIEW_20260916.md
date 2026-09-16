# Ruff Phase 3 Batch 039 — Selection Review (2026-09-16)

Candidate: `tests/test_validation_gates.py`

Ruff inventory:
- I001: 1 (multiline import normalization)
- B008/BLE001/DTZ003/F811/F841: 0

Focused collection: 6 tests, including unknown-gate fail-closed behavior, explicit skip semantics, and deterministic NFC-safe serialization.

Risk: LOW. Test-only validation/policy contract boundary. Proposed edit is import formatting only; no gate behavior, assertions, fixtures, or runtime code changes.

Validation after approval: targeted Ruff, py_compile, focused pytest, git diff --check, secret scan, and diff scope review.

Production: NONE  
Recovery: SAFE HOLD  
No source edit before Gate.
