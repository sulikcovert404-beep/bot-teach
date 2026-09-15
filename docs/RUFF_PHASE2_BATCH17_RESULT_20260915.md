# Ruff Phase 2 Batch 17 Result — 2026-09-15

File: `app/services/observability.py`

Before: one UP035 finding for `Callable` and `Mapping` imported from `typing`.
After: zero UP006/UP035 findings; both imports now come from `collections.abc`. `Any` and `Protocol` remain from `typing`.

Behavior impact: none. Logging, metrics, tracing, serialization, error handling, and runtime structure are unchanged. Diff review confirms import-only change.

Validation:
- Ruff targeted UP006/UP035: PASS
- py_compile: PASS
- Focused tests (`tests/test_observability.py`, `tests/test_telegram_observability.py`, `tests/test_metrics.py`): PASS (7 tests reported; run completed without failures)
- Import/runtime and serialization review: PASS
- Secret scan: PASS (no embedded credential pattern)
- Static typing/Python 3.12: NOT AVAILABLE
- `git diff --check`: PASS

Decision: Batch 17 implementation complete. Production/recovery impact: NONE.
