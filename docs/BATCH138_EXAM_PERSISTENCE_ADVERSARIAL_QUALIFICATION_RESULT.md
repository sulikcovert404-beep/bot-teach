# Gate 138 — Exam Persistence Adversarial Qualification Result

Date: 2026-09-17
Environment: local repository; no server/SSH/Docker/production access

## Test-first evidence

Existing focused validation remains green:

- Gate 136 persisted core tests: PASS
- Gate 137 route and full-suite validation: 979 collected, 974 passed, 5 skipped, 0 failed

A repository search found no existing application-level adversarial tests covering the complete Exam Attempt/Result flow. The available assignment contract tests cover tenant, membership, entitlement, publication and close-time predicates only.

## Required adversarial matrix

| Scenario | Result | Evidence/limitation |
|---|---|---|
| concurrent attempt start | NOT QUALIFIED | no PostgreSQL transaction harness; SQLite cannot prove row-lock behavior |
| atomic attempt numbering | RISK FOUND | implementation computes `MAX(attempt_no)+1`; unique constraint is last guard |
| unassigned student | PARTIAL | service checks profile and class membership; no route-level adversarial test |
| wrong class / tenant | PARTIAL | service predicates include assignment tenant/class membership; no route-level test |
| removed membership | NOT QUALIFIED | no canonical revoke/remove E2E fixture |
| other student's result | PARTIAL | route filters attempt by authenticated student/tenant; no adversarial route test |
| publish/close boundaries | PASS (predicate level) | assignment contract coverage; no full attempt E2E |
| teacher result visibility | NOT QUALIFIED | no dedicated persisted result-visibility test |
| student progress/result visibility | NOT QUALIFIED | no dedicated persisted result-visibility test |
| legacy direct `exam_id` bypass | PARTIAL | route resolves a unique authorized assignment before service call; no negative E2E |
| duplicate submit/idempotency | PARTIAL | service returns existing result by attempt; no concurrent duplicate-submit test |

## Code observations

`app/services/exam_attempts.py::start_attempt` selects `MAX(attempt_no)` and inserts the next number. `with_for_update()` is present, but its effectiveness and race behavior require a real PostgreSQL transactional qualification. The unique constraint prevents duplicate identity only if the race reaches the database; the service has no typed retry/reuse path for an integrity conflict.

No bounded production fix was applied because selecting reuse-versus-new-attempt semantics and qualifying concurrency require a separate decision or real PostgreSQL harness. No schema, migration, auth, API, provider, server, or production change was made.

## Validation

- Full suite baseline: 979 collected / 974 passed / 5 skipped / 0 failed / exit 0
- No code changes
- No production impact
- Gate 138 commit: HOLD

## Verdict

`STOP / ESCALATE — ADVERSARIAL EXAM QUALIFICATION INCOMPLETE; CONCURRENCY RISK REQUIRES REAL POSTGRESQL OR EXPLICIT DOMAIN DECISION`

## Additional read-only validation (2026-09-17)

- 	ests/test_exams_route.py + 	ests/test_assignment_contract.py: 5 passed, 1 upstream deprecation warning, exit 0.
- No source, schema, migration, server, or production changes.
- PostgreSQL concurrency and remaining adversarial scenarios remain unqualified.


- Additional focused suites: 20 passed, 4 skipped, 0 failed, 1 upstream deprecation warning (exit 0).


## Read-only route audit (2026-09-17)

- Legacy /{exam_id}/submit resolves exactly one published, tenant-matched Assignment through AssignmentTarget → Classroom → ClassMembership → StudentProfile before calling attempt services; direct exam_id bypass is denied when no unique authorized assignment exists.
- Student attempt/save/submit/result routes constrain attempt queries by authenticated student_id and resolved tenant_id.
- This is code-path evidence; full application E2E and PostgreSQL concurrency remain pending.


## Constraint audit (2026-09-17)

- ExamAttempt has unique (assignment_id, student_id, attempt_no) and ExamResult.attempt_id is unique.
- Allocation remains read MAX + insert; the unique constraint is a guard, not proof of race-free allocation. Without a real PostgreSQL concurrent harness, atomic numbering is NOT QUALIFIED and no fix was applied.

