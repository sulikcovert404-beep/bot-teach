# Ruff Phase 2 Batch 6 Selection Review — 2026-09-15

## Candidate
`app/services/change_impact.py`

## Inventory
One `UP035` finding: `Mapping` imported from `typing`; current remaining inventory is 901 findings.

## Coupling / blast radius
This module contains immutable change-impact records and a pure impact evaluator. Repository references are limited to `tests/test_change_impact.py`; it is not imported by routes, migrations, deployment scripts, or provider/runtime adapters. Blast radius: LOW-MEDIUM.

## Risk
The import-only change must preserve mapping checks, impact outcome precedence, digest validation, secret detection, and Persian Unicode handling. No side effects or external I/O are present.

## Recommendation
Approve a bounded Batch 6 implementation touching only this file and only UP006/UP035 import modernization.

Required validation: targeted Ruff, `py_compile`, focused change-impact tests, contract/outcome/digest diff review, secret scan, and static type validation if available. Python 3.12/static tooling may be unavailable locally and must be reported.

No production, recovery, migration, dependency, workflow, or broad autofix changes. Production impact: NONE. Recovery: SAFE HOLD. Commander decision required before implementation.
