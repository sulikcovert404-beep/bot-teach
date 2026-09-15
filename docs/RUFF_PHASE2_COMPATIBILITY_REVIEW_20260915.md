# Ruff Phase 2 Compatibility Review

Date: 2026-09-15  
Status: Review only; Phase 2 implementation not authorized

## Findings

- Current target: Python 3.12 (`pyproject.toml`, mypy configuration, CI setup).
- Current Ruff inventory: **907** `UP006`/`UP035` findings across application, migrations, tests, and scripts.
- The repository already uses modern built-in generics (`list[...]`, `dict[...]`) in many modules, so the findings are concentrated in legacy annotations/imports rather than one uniform style.
- `UP035` commonly targets deprecated imports from `typing` (for example `Sequence`, `Mapping`, `Tuple`, `Union`); replacing them can affect runtime imports and Protocol signatures.
- FastAPI/Pydantic annotations and migration modules require import-time compatibility checks; annotations are not uniformly postponed.

## Compatibility Risks

| Area | Risk | Required check |
|---|---|---|
| Python target | Low if constrained to Python 3.12 | compile and supported-runtime test |
| Runtime annotation evaluation | Medium | inspect modules without postponed annotations |
| Protocol/adapters | Medium | mypy and signature tests after each tranche |
| FastAPI/Pydantic schemas | Medium | route import and request-model tests |
| Alembic scripts | Medium | import and migration smoke checks |
| Broad auto-fix | High | prohibited; may alter public contracts |

## Affected Surface

The largest concentrations are in `app/services`, followed by API routes and migration/support scripts. No Phase 2 file was changed during this review.

## Recommendation

Hold implementation until a separate Phase 2 GO. Start with one bounded module group whose annotations are already covered by tests. For each change: review diff, run `py_compile`, Ruff selected rules, mypy, targeted route/contract tests, and a clean full regression. Preserve public Protocol variance and runtime annotation behavior.

## Explicit Hold

No `UP006`/`UP035` auto-fix, Ruff configuration change, workflow change, dependency update, Production action, or Recovery action was performed.

Production impact: `NONE`.
