# Ruff Phase 2 Batch 36 Result — 2026-09-15

File: `app/services/runtime_entry_decision.py`

Before: 1 `UP035` (`Mapping` imported from `typing`). After: 0 `UP006/UP035` findings.

Change: moved only `Mapping` to `collections.abc`; `Any` remains from `typing`.

Validation:

- Targeted Ruff `UP006/UP035`: PASS
- `py_compile`: PASS
- Focused runtime-entry suite: **32 passed / 0 failed** with `PYTHONPATH=.`
- Import-only diff and entry-decision/hash/reference/serialization behavior review: PASS
- `git diff --check`: PASS
- Secret scan: PASS
- Python 3.12/type validation: not available (host Python 3.13)

Production impact: NONE. Recovery: SAFE HOLD. No migration, dependency, configuration, workflow, or production changes.
