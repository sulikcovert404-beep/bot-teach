# BATCH126 — Teacher Legacy Fallback Path Audit

Date: 2026-09-17
Mode: audit + existing-test qualification only

## Inventory

Repository search found no production `legacy` or `fallback` Teacher route/service branch. Teacher routes are mounted canonically from `app/api/routes/teacher.py`; authorization is enforced through the standard role guards and teacher scope helpers. The word `fallback` appears in unrelated provider/Telegram/test compatibility contexts, but no Teacher runtime fallback path was identified.

| Area | Trigger | Runtime reachability | Status |
|---|---|---|---|
| `app/api/routes/teacher.py` canonical routes | normal request | production reachable | CANONICAL_SAFE |
| `app/security/teacher_scope.py` scope helper | class/tenant authorization | production reachable | CANONICAL_SAFE |
| `app/domain/assignment.py` teacher ownership helper | assignment ownership check | service reachable | CANONICAL_SAFE |
| legacy Teacher fallback route/service | no implementation found | none | TEST_ONLY / NOT PRESENT |
| provider fallback routing | provider failure/quota | separate AI gateway, not Teacher authorization | OUT OF SCOPE |
| Telegram safe fallback | unknown callback/navigation | Telegram layer, not Teacher flow | OUT OF SCOPE |

## Contract comparison

Canonical Teacher paths preserve role authorization, tenant/class ownership, publish/close lifecycle, exam state, and feedback boundaries. No alternate Teacher response contract or bypass was found. No security-sensitive fallback path was identified.

## Existing focused qualification

- Teacher-focused and pilot authorization/content tests: **20 passed, 1 warning**.
- Warning: upstream Starlette TestClient/httpx deprecation.
- No tests were added or modified.

## Gaps and decision

A dedicated legacy-fallback test matrix does not exist because no production Teacher fallback branch was found. If a future compatibility route is introduced, it needs explicit trigger, authorization, and response-contract tests before being enabled.

No production, server, SSH, Docker, database, migration, environment, provider, or Secure Role Preview changes were made.
