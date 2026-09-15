# Ruff Phase 2 Batch 46 Selection Review — 2026-09-15

Candidate: `app/services/workflow_orchestration.py`

Finding count: exactly 1 `UP035` (`Callable` imported from `typing`).

Imported symbols: retain `Any` from `typing`; move only `Callable` to `collections.abc`.

Blast radius: LOW. Import-only modernization at the workflow orchestration boundary.

Contract/runtime risks: preserve workflow transitions, authorization calls, orchestration outcomes, serialization, and runtime semantics. No control-flow, dependency, or configuration changes.

Focused tests: locate workflow/orchestration and authorization tests before implementation and run them after the import-only edit.

Required validation: targeted Ruff (`UP006`, `UP035`), `py_compile`, focused tests, import-only diff review, workflow/authorization/outcome/serialization/runtime review, `git diff --check`, secret scan, and Python 3.12/static typing when available.

Production impact: NONE. Recovery impact: SAFE HOLD.

Recommendation: approve implementation only for moving `Callable` to `collections.abc`; retain `Any` from `typing`.
