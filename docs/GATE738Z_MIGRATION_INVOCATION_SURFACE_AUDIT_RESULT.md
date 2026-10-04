# Gate738Z — Migration Invocation Surface Audit

Date: 2026-10-04
Mode: READ-ONLY ONLY
Workspace: D:/project/ai-teacher-gate731-target
Branch / HEAD: codex/gate731-target / e4140c4d55a2943c53ecc187a28729663073d48d

## Verdict

UNSAFE_MIGRATION_ENTRYPOINT_FOUND

Additional findings:
- CI_MIGRATION_PATH_BLOCKED
- DOCUMENTATION_MIGRATION_DRIFT
- UNKNOWN_MIGRATION_SURFACES: 0

The staged Gate738P runner is allow-listed and its contract migrations enforce database-side OLD-fence and candidate-state preconditions. However, active restore and migration instructions invoke Alembic directly, the test-only Gate738P DB matrix accepts an unrestricted admin URL, and the checked-in CI/image path does not establish a successful staged migration before publishing an image.

## Candidate Preservation Precheck

- Gate738V manifest SHA-256 before audit: E7720C946F0D84F683DADBF344346779E8DE2DA6E5B5E21DE77858C0B9CAB378
- Candidate paths: 407
- Verification inputs: 5
- Total entries independently checked for exact size and SHA-256: 412
- Matches: 412/412
- Mismatches or missing files: 0
- Gate738Z report path present in the manifest: NO
- Report path existed before audit: NO
- Current manifest hash remains the accepted value above.

The current workspace therefore matches the frozen manifest and the separate five verification inputs. The 412 total comprises 407 candidate paths plus five verification inputs.

## Current Migration Metadata

- Read-only command: python -m alembic heads
- Result: one head, 20261004_0033
- No database connection or migration command was run.

## Invocation Inventory

| Surface | Classification | Target source and caller | Can reach production-like DB? | Finding |
|---|---|---|---|---|
| scripts/gate738p_contract_upgrade.py:155-203 | RELEASE_CAPABLE | Required EXPECTED_MIGRATION_HEAD, allow-listed to 20261003_0029, 20261004_0032, 20261003_0030, 20261003_0031, or 20261004_0033. Invoked as a staged one-shot runner. | YES, if an operator supplies a production-like DATABASE_URL; this source has no host/environment allowlist. | Strong in-process guards: exact target allowlist; exact candidate readiness parent for contract targets; hard-crash evidence for 0033; no implicit head. |
| migrations/gate738p_contract_guard.py:23-146 and migrations/versions/20261003_0030*, 20261003_0031*, 20261004_0033* | RELEASE_CAPABLE GUARD | Called by contract migrations, not an invocation by itself. | YES, through the invoking Alembic connection. | Contract requires non-app_runtime migration identity, OLD generation FENCED, candidate SERVING with a live session, no other admissible generation, and no old transaction. This protects direct contract migration calls at the database layer but does not replace the runner's candidate HTTP readiness check. |
| docker-compose.yml:47-65 | RELEASE_CAPABLE | migration-gate profile; EXPECTED_MIGRATION_HEAD must be supplied; command points at scripts/gate738p_contract_upgrade.py. | NO via the checked-in default service wiring, which targets the local db service; arbitrary command/environment overrides were not treated as the configured path. | Profile prevents normal API startup from automatically running migration, and the command delegates to the allow-listed runner. The built image does not contain the referenced runner (see Dockerfile finding below), so this path is not operational from the checked-in image. |
| Dockerfile:4-10 | ARTIFACT / INVOCATION DEPENDENCY | Image copies migrations and only scripts/gate738p_crash_writer.py. | N/A | scripts/gate738p_contract_upgrade.py is not copied, although Compose executes that path. No volume mounts the host scripts directory. The image also omits the Gate738P hard-crash evidence file required by the runner for target 20261004_0033. The migration service therefore cannot complete its intended staged path from this image. |
| .github/workflows/ci.yml:35-49 | TEST_ONLY | Direct Alembic upgrade to fixed 20260912_0021, downgrade -1, and re-upgrade against ci-migrations.sqlite. | NO in the defined workflow; it uses a job-local SQLite file. | Explicit but historical test target; it does not qualify the current 0033 staged release path. |
| .github/workflows/ci.yml:123-155 | TEST_ONLY / STAGING SMOKE | Copies .env.example, appends 20260912_0021, then runs Compose db, redis, migrate, api. | NO in the defined GitHub runner; the Compose DB is the job-local db service. | 0021 is outside the Gate738P target allowlist. Independently, the built image omits the migration runner file. This workflow cannot demonstrate a successful current staged migration. |
| .github/workflows/ci.yml:51-93 | RELEASE-CAPABLE IMAGE PUBLISH | The Docker job has needs: quality; push to GHCR is enabled for master. | N/A for a database connection. | It does not depend on staging-smoke. An image can therefore be published without the migration smoke job succeeding: CI_MIGRATION_PATH_BLOCKED. |
| scripts/staging-smoke.ps1:6-42 | TEST_ONLY / LOCAL COMPOSE | Requires a caller-provided expected head; starts db, migrate, and api and compares readiness output. | NO through its checked-in local Compose path. | No silent target fallback. The Compose service still receives the value from .env, so a separate caller value does not itself reconcile .env or bypass the runner. |
| scripts/restore-drill.ps1:3-57 | RESTORE_ONLY | Required MigrationTarget passes only a character-pattern check, then directly executes python -m alembic upgrade MigrationTarget against RestoreDatabaseUrl. | YES. URL validation only rejects a database path ending in education; other production-like database names/hosts are not excluded. | Not routed through Gate738P; accepts arbitrary targets, including head; readiness checks status but never verifies migration_head equals MigrationTarget. pg_restore uses --clean. Requires a repair gate. |
| docs/MIGRATIONS.md:17-27 | DOCUMENTATION_ONLY / RELEASE GUIDANCE | Prescribes docker compose run --rm api alembic upgrade <revision_id>. | YES if the Compose DB URL is configured to a production-like target. | Direct API-service Alembic invocation bypasses the migration-gate runner and target allowlist. The neighboring prose says staged checks are required, so the command and policy contradict each other. |
| docs/OPERATIONS.md:31-57, 59-77 | DOCUMENTATION_ONLY / RESTORE AND RELEASE GUIDANCE | Shows direct host Alembic upgrade and the restore-drill wrapper. | YES if the supplied URL points to a production-like database. | The script does not enforce the document's claim that the target is approved or verify the exact resulting head. Release wording does not identify the staged runner as the required invocation. |
| tests/test_gate738p_contract_guard.py:18-35, 100-185 | TEST_ONLY | Reads GATE738P_ADMIN_URL and, when set, creates/drops a database and role, prepares 0032, and invokes 0030. It skips only when the variable is absent. | YES. The URL is not restricted to loopback or a disposable database name. | A mistakenly configured production-like admin URL would receive destructive test DDL and migration activity. Add an explicit URL/host/database safety guard in a separate repair gate. |
| tests/test_gate738p_hard_crash_qualification.py:190-204, 212-365 | TEST_ONLY / ENVIRONMENT-A QUALIFICATION | Exact revision targets through the Gate738P runner; requires loopback PostgreSQL and uses a generated gate738e_gate738p database and candidate role; also exercises Docker lifecycle. | YES only if the loopback endpoint is externally forwarded; source enforces a loopback URL but cannot identify the listener behind it. | Environment-required qualification harness. Not run in this read-only audit. |
| tests/test_gate735b_class_enrollment_postgres.py:32-36, 257-260 | TEST_ONLY | Gate-specific loopback PostgreSQL fixture; explicit 0026/0025 commands, with one upgrade-to-head call at line 259. | YES only if the configured loopback port is externally forwarded; otherwise its Gate-specific local fixture is intended. | The head call is test-only, not a release entrypoint, but violates the explicit-target convention and can drift as new revisions are added. |
| tests/test_gate736a_integrated_candidate_postgres.py; tests/test_submission_revision_lifecycle.py; tests/test_submission_revision_migration.py; tests/test_tenant_context_foundation_postgres.py | TEST_ONLY | Gate-specific local/loopback disposable fixtures with explicit revision strings and skip when the required Gate PostgreSQL port is absent. | YES only if the configured loopback port is externally forwarded; otherwise local disposable fixture. | Classified individually by file and direct Alembic callsites. These are not release entrypoints. No migration tests were executed. |
| tests/gate738f_{qualification,lock,recovery,concurrency}.py and tests/gate738h_{qualification,acl_matrix,backfill_recovery,lock_matrix,failure_injection}.py | RETIRED | Direct-entry guards print retired guidance and exit. Search found helper imports only among these retired F/H scripts. | NO through direct execution; the retired entrypoint exits before the database work. | No live wrapper bypass to these runners was found. Their historical command text is not an active qualification path. |
| scripts/backfill_submission_revisions.py:1-35, 90-110 | TEST_ONLY / DISPOSABLE BACKFILL | Requires GATE738E_DISPOSABLE=1, loopback host, and a gate738e_* database name; also validates permitted expand revisions. Called from disposable test harnesses. | NO under the source-enforced direct URL and database-name checks. | Adjacent data-backfill tool, not an Alembic CLI command; bounds the operation before opening its database connection. |
| app/api/routes/health.py and tests/test_health.py | READ_ONLY / TEST FIXTURE | Read current Alembic metadata/version for readiness; test uses mocked result. | Read-only only. | Not migration invocation surfaces. |
| app/core/config.py, app/api/routes/vps_canary_deployment.py, migration definitions, .env.example, and historical Gate reports | CONFIGURATION / METADATA / DOCUMENTATION | Expected-head settings, string labels, migration revision declarations, or historical report examples. | No direct DB write path. | Classified separately from executable invocations. .env.example and README still name 20260912_0021, which is stale relative to 0033 and incompatible with the Gate738P allowlist. |

## Release and Restore Controls

PASS:
- Gate738P runner rejects an empty or non-allow-listed target.
- It has no upgrade-head path or missing-target fallback.
- Contract targets require candidate health at their exact predecessor.
- Contract migration code separately enforces durable writer-generation and transaction preconditions.
- The normal API service has no automatic migration command.
- The old Gate738F/H direct runners are retired fail-closed.

BLOCKED / UNSAFE:
- The migration runner referenced by Compose is absent from the Docker image.
- The 0033 evidence file is also not copied or mounted into the migration container.
- CI staging-smoke pins 0021, which the current staged runner rejects.
- The image publish job is not dependent on staging-smoke.
- Active migration and restore documents provide direct Alembic commands that bypass the staged runner.
- restore-drill accepts arbitrary MigrationTarget and does not verify the resulting exact revision.
- Gate738P database integration tests accept arbitrary GATE738P_ADMIN_URL and can create/drop database objects on the target.
- One test-only upgrade-head call remains in Gate735B; no release-capable upgrade-head command was found.
- README and .env.example retain 0021 references despite the sole workspace head being 0033.

## Scope and Validation

Read-only work performed: source and documentation searches; Compose, Dockerfile, workflow, test, runner, and guard inspection; frozen-manifest file/size/hash verification; python -m alembic heads.

Not performed: Docker commands or lifecycle; DB connection or writes; Alembic upgrade/downgrade/stamp/current; SSH; Compose config execution; source/Compose/workflow changes; tests; commit; deployment.

Candidate files and manifest were not modified. Only this audit report was created.

## Risk

The staged migration runner itself contains strong gates, but the repository does not consistently force callers through it. The current image cannot execute the configured migration command, while CI can publish without the smoke job; active direct instructions and the restore helper leave a separate route around candidate readiness and target allowlisting. The unrestricted test admin URL creates a second environment-misconfiguration hazard. These issues prevent a clean invocation-surface verdict.

## Recommended Resolution

Issue one separate, scoped repair Gate covering:
1. Packaging the exact staged runner and a safely supplied 0033 hard-crash evidence file into the migration job.
2. Aligning staging-smoke with the current explicitly approved Gate738P path and making image publication depend on its required qualification.
3. Replacing direct Alembic instructions with the migration-gate invocation.
4. Restricting restore-drill to an allow-listed revision and verifying the final revision equals the requested target.
5. Adding fail-closed loopback/database-name validation to GATE738P_ADMIN_URL test setup.
6. Replacing the remaining test-only upgrade-head target with an exact fixture revision.

No repair was made under this audit-only Gate.

## Final

MIGRATION COMMAND SURFACE CLEAN: NO
REPAIR GATE REQUIRED: YES

