# BATCH067 — Ruff Debt Prioritization Audit

Mode: local/read-only inventory. No code changes, auto-fix, server, deployment, migration, environment, database, or commit action.

## Fresh inventory
| Rule | Findings | Affected modules |
|---|---:|---:|
| F401 | 474 | 153 |
| C408 | 80 | 80 |
| UP017 | 29 | 9 |
| UP045 | 10 | 4 |
| **Total Ruff** | **1868** | — |

## F401 classification (conservative line/import audit)
- Real and potentially removable: 220 findings / 132 modules — primary candidates for a later focused wave.
- Framework/plugin registration: 155 / 58 — defer; removal may alter registration or API behavior.
- TYPE_CHECKING/typing-related: 59 / 46 — defer pending type-check validation.
- Import for side effect: 0 / 0.
- Uncertain: 40 / 29 — manual review required.

## Candidate guidance
Start a future wave with a small subset of the 220 potentially removable findings after per-module usage and side-effect review. Keep framework/plugin, typing, uncertain, routes with auth implications, migrations, and runtime-sensitive modules out of an automatic fix wave.

## Acceptance
Inventory is reproducible; no semantic changes made. Next cleanup wave is clearly defined as a reviewed F401 subset, with focused tests and full regression required after any code changes.

Commit Gate 067: HOLD pending Commander approval.
