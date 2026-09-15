# Ruff Baseline Remediation Assessment

Date: 2026-09-15  
Mode: Read-only assessment; no lint or workflow changes

## Current Status

The CI quality job runs:

```text
python -m ruff check app tests migrations scripts
```

The current local Ruff run reports **3,074 findings**. This is an existing repository baseline, not a failure introduced by Browser E2E files.

## Failure Source

The dominant rule families are:

| Rule | Count | Typical scope |
|---|---:|---|
| I001 | 796 | import ordering/formatting |
| UP006 | 758 | modern typing syntax |
| F401 | 519 | unused imports |
| B008 | 248 | call expressions in defaults |
| UP035 | 149 | deprecated typing imports |
| ASYNC230 | 139 | blocking file operations in async code |
| ASYNC210 | 129 | blocking network calls in async code |
| C408 | 80 | unnecessary `dict()` calls |
| BLE001 | 35 | broad exception catching |
| Other rules | 221 | mixed style, safety, and modernization findings |

Counts are diagnostic only; no automatic fixes were applied.

## Baseline Difference

The workflow has enforced the same broad command since earlier CI hardening and currently includes `scripts` in addition to application, tests, and migrations. No scoped per-directory ignores or baseline file exists in `pyproject.toml`. Therefore legacy findings fail the quality job before later checks run.

## Remediation Paths

1. **Inventory and ownership:** group findings by package and assign owners before editing behavior-sensitive code.
2. **Low-risk tranche:** address import ordering, unused imports, and mechanical syntax modernization in small commits.
3. **Behavior-review tranche:** review FastAPI defaults, async blocking calls, broad exception handling, and timezone rules individually; do not bulk auto-fix.
4. **Quality rollout:** use a reviewed baseline/changed-lines policy only if Commander approves it; retain a full-lint debt report so existing debt is visible.
5. **Regression evidence:** run targeted tests for each tranche, then full regression before changing the merge gate.

## CI Impact

Until remediation or an approved baseline policy is introduced, the overall CI workflow remains **PARTIAL** even though the isolated Browser E2E job is green. This assessment does not alter that gate.

## Prohibited in This Task

- changing Ruff configuration or ignores;
- auto-fixing source files;
- changing CI workflow behavior;
- dependency updates;
- production or Recovery actions.

## Recommendation

Open a separate Commander-approved Ruff remediation gate. Start with a measured, directory-scoped low-risk tranche and preserve the current full-lint evidence. Do not claim the quality gate is green until a subsequent CI run proves it.

## Production Impact

`NONE`.
