# Gate724N — First Product Slice Contract

## Verdict

`PRODUCT_724_IMPLEMENTATION_READY`

This is a design and contract artifact only. No code, schema, runtime, deployment, or environment mutation is part of this gate.

## Frozen slice

The first product slice is the student journey:

`Student Identity → School/Class Context → Assignment Access → Learning/Assignment Activity → Progress Persistence → AI Tutor Question → Citation-backed Answer → Return to Assignment/Progress Context`

In scope are authenticated student identity, tenant and class membership checks, published assignment discovery/detail/resume/submission, exam attempt activity, tutor access with database-backed retrieval and citations, usage/audit persistence, and progress/history read models. Out of scope are teacher authoring, school administration, billing, role changes, migrations, new AI providers, production/staging changes, domain/edge work, and cross-student or cross-school administration.

## Stage contract and current evidence

| Stage | Existing entry point / service / model | Authorization and persistence | Status | Gap |
|---|---|---|---|---|
| Student identity | `POST /api/v1/auth/telegram`; `app/api/routes/auth.py`; `User`, `Identity`, `UserTenantMembership` | Telegram initData validation; user lookup/create; JWT role claim; commit | READY | Client must retain token and reject invalid identity |
| School/class context | `GET /api/v1/student/profile`, `GET /api/v1/student/v2/classroom-content`; `enforce_tenant`; `StudentProfile`, `ClassMembership`, `Classroom`, `SchoolTenant` | STUDENT role, tenant resolution, active class membership; read-only | READY | UI must show the resolved school/class context explicitly |
| Assignment access | `GET /api/v1/student/v1/assignments`, `GET /api/v1/student/v1/assignments/{id}` | `ASSIGNMENT_ACCESS`, published status, target classroom and student membership; read-only | READY | Client needs a single consistent assignment list/detail state |
| Learning / assignment activity | `GET .../{id}/resume`, `POST .../{id}/submissions`; exam attempt start/answer/submit routes | STUDENT plus tenant/member/owner checks; `StudentSubmission`, `ExamAttempt`, audit records; commits | READY | UI orchestration and idempotent retry behavior must be covered end to end |
| Progress persistence | `GET /api/v1/student/progress`, `/tutor/history`; `BetaQualityAudit`, `AIUsageEvent`, `ExamAttempt`, submission records | Entitled student read; tutor calls persist usage and quality audit | READY | The slice deliberately freezes progress as a read model derived from existing activity/audit entities; provenance and empty-data behavior are part of the response contract |
| AI tutor question | `POST /api/v1/tutor/answer`; `AITutor`, `DatabaseRetriever`, Gemini provider | `BOOK_QA` entitlement, safety limits, provider availability; usage and beta audit commit | READY | Ensure assignment/class context is supplied by the client and reflected in retrieval scope |
| Citation-backed answer | `TutorResponse.citations`; retriever/provider result | Citation objects include source/chunk/page/chapter/lesson; no answer is accepted as citation-backed when the list is empty | READY | Client must render citations and distinguish no-citation/provider failure |
| Return to assignment/progress | Mini-app/platform provider calls assignment, tutor and progress endpoints | Same bearer/tenant checks on every call | PARTIAL | UI state transition and deep-link back to assignment need focused acceptance coverage |

## API inventory

All routes are under `/api/v1` in the application router.

| Method | Path | Role/access | Request | Success | Errors / idempotency / persistence |
|---|---|---|---|---|---|
| POST | `/auth/telegram` | public verification endpoint | Telegram initData | JWT, user, role | 401 invalid/expired data; user bootstrap is the only identity write |
| GET | `/student/v1/assignments` | STUDENT + `ASSIGNMENT_ACCESS` | bearer | published assignments visible to member | 401/403 auth or entitlement; read-only |
| GET | `/student/v1/assignments/{assignment_id}` | STUDENT + entitlement | path id | assignment snapshot and status | 404 outside membership/published; read-only |
| GET | `/student/v1/assignments/{assignment_id}/resume` | STUDENT + entitlement | path id | active exam attempt or null | 404 inaccessible; read-only |
| POST | `/student/v1/assignments/{assignment_id}/submissions` | STUDENT + entitlement | submission content | created/upserted submission | 404/409 inaccessible/closed; retry must preserve revision semantics |
| POST | `/student/exam-assignments/{id}/attempts` | STUDENT | path id | new attempt | tenant/member checks; commit; duplicate/retry behavior covered by attempt service |
| PATCH | `/student/exam-attempts/{id}/answers` | STUDENT owner | answer payload | saved answers | 403 cross-student; commit |
| POST | `/student/exam-attempts/{id}/submit` | STUDENT owner | none | submitted attempt/result | 403 cross-student; commit |
| GET | `/student/progress` | entitled student | bearer | mastery/history aggregate | 401/403; empty-data response must be stable |
| POST | `/tutor/answer` | `BOOK_QA` | `{query,max_tokens}` | text, model, citations, access, usage | 401/403; 503 provider unavailable; usage and audit commit; no duplicate charge on client retry is currently not guaranteed |
| GET | `/tutor/history` | `BOOK_QA` | bearer | prior tutor activity | 401/403; read-only |

## Data contract

Existing entities are sufficient for this slice: `User`, `Identity`, `UserTenantMembership`, `SchoolTenant`, `StudentProfile`, `Classroom`, `ClassMembership`, `Assignment`, `AssignmentTarget`, `AssignmentSnapshot`, `StudentSubmission`, `ExamAttempt`, `ExamResult`, `AIUsageEvent`, `BetaQualityAudit`, and `AuditLog`.

`SCHEMA_CHANGE_REQUIRED = NO` for the first implementation. Progress is explicitly a derived read model over existing `ExamAttempt`, `StudentSubmission`, `AIUsageEvent`, and `BetaQualityAudit` records; it is not a new canonical table. Tutor context is request-level data and requires no persistence schema. A dedicated progress entity or citation table is out of scope and would require a later gate. No migration is authorized here.

## Authorization and negative contract

Every student request must derive identity from the verified bearer subject, resolve tenant scope, and enforce membership/ownership. The following must fail closed: reading or mutating another student's progress/attempt, reading an assignment targeted to another school/class, teacher-only or school-admin operations through student credentials, invalid or tampered Telegram/JWT identity, and IDs belonging to another tenant. Expected outcomes are 401 for invalid identity and 403/404 according to existing route semantics; no information-bearing cross-tenant response is allowed.

## AI tutor contract

The client sends a non-empty bounded question plus `student_id`, `school_id`, `classroom_id`, and optional `assignment_id` context in the request-level contract. The server derives the authenticated student from the bearer, verifies every supplied object belongs to that student/tenant/class membership and assignment target, authorizes `BOOK_QA`, applies safety limits, retrieves only from the authorized curriculum scope through `DatabaseRetriever`, calls the configured provider, and returns `{text, model, task_type, citations[], access, usage}`. Each citation must identify source/chunk and available page/chapter/lesson metadata. Empty retrieval is represented explicitly as an empty citation set with an `EMPTY_CONTEXT` client state; provider/configuration failure is 503 and must not be persisted as a successful answer. Successful calls persist usage and redacted quality audit records. Raw secrets and raw credentials are never returned or persisted.

## End-to-end acceptance

1. A valid Telegram identity obtains a token and sees the correct student role, tenant, and class.
2. The student sees only published assignments targeted to a joined classroom.
3. Opening an assignment, resuming/starting activity, saving answers, submitting, and returning to the assignment works with durable state.
4. A tutor question from that context returns a citation-bearing answer; the client renders citations and preserves assignment/progress navigation.
5. Progress/history reflects persisted tutor and assignment activity, including a stable empty state for a new student.

The same scenario is the executable A+B+C acceptance contract: one student authenticates, opens a published assignment targeted to a joined class, resumes or performs activity, submits/reloads, asks a context-bound tutor question, receives a citation-backed answer, navigates back, reloads the assignment/progress view, and observes the same durable activity. Assertions include tenant/object authorization, persisted activity, citation metadata, and no false-success state on empty retrieval/provider failure.

Failure scenarios: invalid initData; expired token; cross-school assignment ID; cross-student attempt ID; closed assignment; provider unavailable; empty retrieval; duplicate submission/retry; concurrent answer updates; and entitlement denial. All must remain fail-closed and leave no unauthorized write.

## Test matrix (definition only)

| Layer | Required checks |
|---|---|
| Unit/service | initData/JWT, tenant resolution, assignment visibility, tutor citation mapping, empty retrieval, provider failure |
| API | route status/payload contracts, entitlement and role failures, submission idempotency semantics |
| Auth/tenant | cross-student, cross-school, invalid identity, teacher/admin misuse |
| PostgreSQL integration | membership joins, snapshot selection, submission/attempt persistence, usage/audit commit |
| Concurrency | concurrent answer/submission retry and duplicate charge protection |
| E2E/browser | Telegram bootstrap → assignment → activity → tutor → citation → progress return |
| Regression | existing auth, mini-app, teacher/admin, exam, tutor and provisioning suites remain green |

## Work packages

1. **Student journey orchestration** — likely `web/mini-app/app.js`, `web/platform/ui/provider.js`, assignment/student route adapters. Wire identity/context/list/detail/resume/activity/progress states. Depends on existing APIs. DoD: acceptance flow and navigation tests pass.
2. **Assignment activity hardening** — `app/api/routes/student.py`, exam/assignment services and focused tests. Make retry and conflict behavior explicit without changing authorization. DoD: submission/attempt negative and concurrency cases pass.
3. **Tutor context and citation UX** — `app/api/routes/tutor.py`, `app/services/ai_tutor.py`, retriever integration, mini-app/platform tutor UI. Preserve citation contract and 503/empty-context behavior. DoD: citation and failure tests pass with no secret leakage.
4. **Progress read-model contract** — student progress/history adapters and tests. Document provenance and stable empty state; do not add schema. DoD: activity-to-progress acceptance and regression tests pass.

Risks are provider latency/availability, existing progress aggregation semantics, retry charging, and tenant leakage. Any schema, privilege, deployment, or runtime change requires a separate gate.

## Boundary and next gate

Implementation is authorized only for the four work packages above after this contract is accepted. No production/staging mutation, migration, commit, deploy, restart, prune, config, env, nginx, Cloudflare, firewall, backup, or `codesho_staging` action is included. Next gate: `Gate725N — Student Core Learning Slice Implementation`.
