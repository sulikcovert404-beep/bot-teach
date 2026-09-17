# BATCH072 — Ruff UP Rule Prioritization Audit

Mode: read-only inventory. No code changes, auto-fix, server/SSH/Docker, deploy, migration, env, DB, or unrelated formatting.

## Inventory
- UP017: 29 findings
- UP045: 10 findings
- Combined: 39 findings across 13 modules

## Classification
- DATETIME-SEMANTIC / RUNTIME-BEHAVIOR-SENSITIVE: all 29 UP017 findings. They alter datetime construction and require timezone/serialization behavior review.
- TYPE/ANNOTATION-SENSITIVE / API-CONTRACT: all 10 UP045 findings. They alter Optional annotation syntax and must be validated against supported Python/type-checking contracts.
- SAFE-AUTO-CANDIDATE: 0
- FRAMEWORK-DEPENDENT: 0
- OTHER-REVIEW: 0

Affected modules include routes and services with runtime/API behavior; no automatic transformation is authorized by this audit.

## Recommendation
Keep UP017 and UP045 deferred. If revisited, use small per-module waves with explicit semantic review, focused tests, py_compile, and full regression. Do not use broad Ruff auto-fix.

Commit Gate 072: HOLD pending Commander approval.
