# EXAM 0021 FINAL RUNTIME E2E QUALIFICATION — 2026-09-14

## Scope
Disposable-only qualification. Production was not contacted or mutated; live DB remains at `20260912_0020` and migration 0021 remains locked.

## Fixture / migration
- Fresh disposable PostgreSQL project was migrated explicitly from baseline to `20260912_0021`.
- Fixture was seeded through the privileged disposable PostgreSQL connection, never with `app_runtime`.
- Fixture chain: two tenants, teacher, two students, profiles, classrooms, membership, published assignment and exam question.
- Unique fixture keys were run-specific and cleanup completed with `docker compose -p examfinal down -v --remove-orphans`.

## Restricted runtime evidence
The application service ran with `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`) and transaction-local tenant context. `FORCE ROW LEVEL SECURITY` was enabled on `assignments`, `exam_attempts`, and `exam_results` (and selected tenant tables).

- Student start: PASS; question snapshot present; attempt number 1.
- Save answers: PASS (repeat save PASS).
- Submit: PASS; server grading produced a result.
- Repeat submit: PASS and returned the same persisted result (idempotent).
- Cross-tenant access: DENY PASS.
- Other student access: DENY PASS.
- Missing membership: DENY PASS.
- Invalid tenant context: DENY PASS.
- Persisted attempt visibility under correct context: PASS.

## Concurrency
Two concurrent `start_attempt` calls for the same student and assignment completed with attempt numbers 2 and 3. No duplicate attempt number and no unhandled `IntegrityError` occurred.

## Final gate
```text
Seed: PASS
Runtime: PASS
RLS: PASS
Tenant Isolation: PASS
Concurrency: PASS
Cleanup: PASS
Production Mutation: NONE

FINAL: READY FOR COMMANDER REVIEW
```

Migration 0021 is not deployed to live environments. No production, Cloudflare, webhook, credential, or RLS-live changes were made.
