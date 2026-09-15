# Exam 0021 RLS Request-Context Qualification

Status: FAIL / STOP (read-only audit)  
Production mutation: NONE

## Findings

- `app.db.base.set_tenant_context()` is correctly parameterized and transaction-local (`set_config(..., true)`), validates tenant identifiers, and refuses calls outside an active transaction.
- `app.security.tenant_scope.enforce_tenant()` validates role ownership but only returns a tenant identifier; it does not set the PostgreSQL session context.
- `app.api.routes.auth.get_session()` creates/yields an `AsyncSession` without tenant-context injection.
- `app.services.exam_attempts.start_attempt`, `save_answers`, and `submit_attempt` apply tenant predicates but do not call `set_tenant_context`.
- Repository search found `set_tenant_context` used in `app/api/routes/sources.py`, but no wiring on the Exam request path.

## Consequence

With `FORCE ROW LEVEL SECURITY` on `exams`, `exam_attempts`, and `exam_results`, an Exam request using the restricted runtime role can see no rows or fail writes unless a trusted request boundary sets `app.tenant_id` before the service query. A tenant predicate in application SQL cannot replace database context enforcement.

## Additional integration gap

The Student Exam request path currently receives only canonical subject/role and an assignment or exam identifier. JWT creation records subject and role, not a tenant claim. The first assignment lookup is tenant-owned under the candidate RLS model, so no qualified authoritative tenant source exists before that query. This ordering requires a separate design decision (for example, a server-side identity-to-tenant resolver or explicitly scoped request contract) before wiring can be implemented safely.

## Qualification matrix

| Check | Result |
|---|---|
| Context helper validation | PASS (static) |
| Transaction-local setting semantics | PASS (static) |
| Exam dependency/middleware injection | FAIL / absent |
| Exam service path under RLS | NOT QUALIFIED |
| Missing-context fail-closed SQL behavior | PASS (disposable direct SQL) |
| Production mutation | NONE |

## Decision

STOP. No code, schema, migration, role, deployment, or environment change was made. The next implementation gate must explicitly wire and test request authentication → tenant resolution → transaction-local context → Exam service, then repeat the disposable PostgreSQL E2E/security suite.
