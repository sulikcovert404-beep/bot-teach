# BATCH127 — Teacher Legacy Fallback Contract Qualification

Date: 2026-09-17
Mode: test-focused qualification only

## Gate 126 summary

The Gate 126 audit found no production Teacher legacy/fallback route or service branch. Canonical Teacher routes and scope helpers are the only runtime-reachable paths identified.

| fallback/path | trigger | runtime reachable | canonical contract | fallback contract | classification | existing coverage |
|---|---|---:|---|---|---|---|
| `app/api/routes/teacher.py` canonical routes | normal request | yes | role, tenant, class, lifecycle guards | n/a | CANONICAL_SAFE | PASS |
| `app/security/teacher_scope.py` | class/tenant authorization | yes | fail-closed scope | n/a | CANONICAL_SAFE | PASS |
| `app/domain/assignment.py` ownership helper | assignment operation | yes | teacher and tenant ownership | n/a | CANONICAL_SAFE | PASS |
| Teacher legacy/fallback route or service | none found | no | n/a | n/a | TEST_ONLY / NOT PRESENT | no dedicated path |
| AI provider fallback | provider failure/quota | separate AI gateway; not Teacher authorization | out of scope | out of scope | OUT_OF_SCOPE | existing provider tests |
| Telegram safe fallback | unknown callback/navigation | Telegram layer; not Teacher flow | out of scope | out of scope | OUT_OF_SCOPE | existing Telegram tests |

## Qualification

Existing Teacher-focused and pilot authorization/content tests: **20 passed, 1 warning**. No new tests were required because no fallback implementation exists. The warning is the upstream Starlette TestClient/httpx deprecation.

No contract defect, authorization bypass, cross-tenant path, lifecycle divergence, fabricated success, or production-reachable legacy fallback was found.

## Changes

No production code, tests, server, SSH, Docker, database, migration, environment, provider, or Secure Role Preview changes were made. This report is intentionally uncommitted pending Commander authorization.
