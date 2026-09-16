# Ruff Phase 3 Batch 040 — Selection Review (2026-09-16)

Candidate: `tests/test_subscription_preview_access.py`

Ruff inventory:
- I001: 1 (multiline import normalization)
- B008/BLE001/DTZ003/F811/F841: 0

Focused collection: 3 tests covering free/pro preview entitlement, membership precedence/expiry, and unpublished/missing subscription fail-safe behavior.

Risk: LOW to MODERATE. Test-only entitlement policy boundary; source edit is strictly import normalization. No entitlement behavior, assertions, fixtures, or runtime code will change.

Validation after approval: targeted Ruff, py_compile, focused pytest, git diff --check, secret scan, diff scope review.

Production: NONE  
Recovery: SAFE HOLD  
No source edit before Gate.
