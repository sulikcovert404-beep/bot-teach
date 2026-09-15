# Ruff Phase 2 Batch 40 Selection Review — 2026-09-15

Candidate: `app/services/runtime_execution_lifecycle.py`

Finding count: exactly 1 `UP035` (`Iterable` imported from `typing`).

Imported symbols: `Any` remains from `typing`; only `Iterable` is eligible for modernization.

Blast radius: LOW. Import-only change at the execution lifecycle boundary.

Contract/runtime risks: preserve lifecycle states, transition validation, reference handling, serialization, and execution behavior. No control-flow or dependency changes.

Related tests: identify lifecycle-focused tests before implementation and run them after the import-only edit.

Required validation: targeted Ruff (`UP006`, `UP035`), `py_compile`, focused tests, import-only diff and behavior review, `git diff --check`, secret scan, and Python 3.12/type validation when available.

Production impact: NONE. Recovery impact: SAFE HOLD.

Recommendation: approve an implementation gate limited to moving `Iterable` to `collections.abc`; retain `Any` in `typing`.
