# RUFF PHASE 2 BATCH 47 — SELECTION REVIEW

Date: 2026-09-15

## Candidate
- File: `app/api/routes/beta_1000_expansion.py`
- Findings: exactly 2 `UP035` (deprecated `typing.Dict`, `typing.List`), zero `UP006`.
- Imported symbols: `Any`, `Dict`, `List`, `Optional` from `typing`; only `Dict` and `List` are candidates. `Any`/`Optional` remain unchanged unless separate findings arise.

## Blast radius and risks
The file is a FastAPI beta expansion router with Pydantic request schema and in-memory monitoring/control data. The proposed change is import-only (`Dict`→`dict`, `List`→`list` via `collections.abc`/built-in-compatible annotations as appropriate). No endpoint paths, dependency injection, authorization, response payloads, state transitions, or provider behavior should change. Because this is an API route module, validation must confirm import and route registration semantics; no broad autofix is authorized.

## Focused tests
Search candidates: beta expansion route and expansion-wave tests under `tests/` (if present). Run only discovered relevant files plus compile/import checks.

## Required validation after implementation gate
- Ruff `UP006,UP035` targeted check: zero findings.
- `py_compile` for the module.
- Focused beta expansion/API route tests; record no-test case explicitly.
- Import-only diff and route/authorization/response-shape review.
- `git diff --check` and secret scan.
- Python 3.12/static typing if available; otherwise record unavailable.

## Gate status
Selection Review complete; source edit is **not** performed in this step. Production impact: NONE. Recovery impact: SAFE HOLD. No migration, dependency/config/workflow, deployment, or runtime action.
