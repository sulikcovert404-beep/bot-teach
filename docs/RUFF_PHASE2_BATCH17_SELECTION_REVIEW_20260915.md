# Ruff Phase 2 Batch 17 Selection Review — 2026-09-15

## Candidate

`app/services/observability.py`

## Finding inventory

Ruff `UP006,UP035` reports exactly one finding: `UP035` for `Callable` and `Mapping` imported from `typing`; Ruff offers a safe modernization to `collections.abc` while retaining `Any` and `Protocol` in `typing`.

## Scope and risk

Proposed implementation scope is limited to import modernization in this file. The module is shared observability infrastructure, so blast radius is MEDIUM. Logging, metrics, tracing, event serialization, error handling, and runtime behavior must remain unchanged. No migration, route, provider, configuration, dependency, workflow, deployment, or production changes are included.

## Validation required before implementation gate

- Ruff targeted `UP006/UP035` on this file
- Python compile check
- Focused observability tests (if present)
- Import/runtime smoke and serialization review
- Secret scan
- Static typing/Python 3.12 validation when available
- Diff review confirming only import sources changed

## Decision requested

Commander approval is required before any implementation. This report performs selection only and changes no source code.

Production impact: NONE
Recovery: SAFE HOLD
