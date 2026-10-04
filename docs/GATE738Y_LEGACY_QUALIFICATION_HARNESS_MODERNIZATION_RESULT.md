# Gate738Y — Legacy Qualification Harness Modernization

## STATUS

`PASS — HARNESS_MODEL_MODERNIZED; DATABASE/RUNTIME QUALIFICATION NOT CLAIMED`

## Finding

The current migration graph has one head, `20261004_0033`. Its staged path is:

```text
20261003_0029 (expand/backfill target)
  → 20261004_0032 (writer-admission control plane)
  → 20261003_0030 (guarded contract target)
  → 20261003_0031 (compatibility cleanup target)
  → 20261004_0033 (guarded contract completion)
```

The Gate738P qualification runner already encodes explicit revision targets,
candidate readiness, control-plane drain/fence actions, and hard-crash evidence
for the final target. `python -m alembic heads` reports exactly
`20261004_0033`. The revision `20260924_0023` has no migration file and is not
part of executable lineage.

The Gate738F/H standalone qualification runners predate this control-plane
stage. Their old paths can attempt `0030` without first applying `0032`, omit
candidate identity and drain/fence prerequisites, and in Gate738H print
`0031` as a final PASS head. Those entrypoints are now retired with an explicit
stop message. Their code and earlier result documents remain historical
evidence only; no old runner was executed.

## Evidence and reference classification

| Category | References | Classification / treatment |
|---|---|---|
| Current staged orchestrator | `scripts/gate738p_contract_upgrade.py`, `tests/gate738p_hard_crash_qualification.py`, `tests/test_gate738p_contract_guard.py` | `CURRENT`; explicit `0029`, `0032`, `0030`, `0031`, `0033` targets and fail-closed candidate/fence checks. PostgreSQL cases remain environment-gated. |
| Current lineage guards | `tests/test_health.py`, `tests/test_migration_roundtrip_qualification.py`, `tests/test_gate738y_legacy_harness.py` | `CURRENT`; enforce the one-head `0033` graph, expected target ancestry, and no executable `0023` revision. |
| Old Gate738F/H standalone runners | `tests/gate738f_*.py`, `tests/gate738h_*.py` | `STALE`; direct executable entrypoints now stop and point to the current Gate738P staged path. Historical implementation text is retained for prior evidence and, for the backfill helper, import-only historical reuse. |
| PostgreSQL lifecycle tests | `tests/test_submission_revision_lifecycle.py`, `tests/test_submission_revision_migration.py`, `tests/test_tenant_context_foundation_postgres.py` | `TEST_FIXTURE_ONLY`; explicit disposable PostgreSQL ports are required. `0031` is an intermediate compatibility/cleanup target in those tests, not a declaration of the current release head. |
| Operational/docs references | `docs/MIGRATIONS.md`, `docs/OPERATIONS.md`, `scripts/restore-drill.ps1` | Updated to require an explicit authorized target; generic `upgrade head` execution guidance was removed. Gate738H report now carries a historical-scope notice. |
| Older gate reports and archived operational records | Other dated `docs/GATE738*.md` and older batch/runbook reports | `DOCUMENTATION_ONLY` or `LEGACY_BUT_SAFE`; revision IDs describe evidence at the time and are not current execution instructions. |

The stale assumptions “0030 is runnable before the control plane,” “0031 is
the current release head,” and “one unrestricted upgrade command completes the
release” are no longer executable through the Gate738F/H runner entrypoints or
the generic migration/restore instructions.

## Current harness model

The DB-free Gate738Y model captures this order:

```text
PRE-CONTRACT TARGET (0032)
  → candidate/control-plane eligibility
  → OLD-generation drain and durable fence
  → active-writer and database-quiescence evidence
  → exact contract target (0030, then 0031, then 0033)
```

The model fails closed if candidate eligibility is false/unknown, OLD is not
FENCED, active OLD-writer evidence is unknown/nonzero, or database quiescence
is unknown/false. A passing model test is not a PostgreSQL test and does not
certify lock timing, migration execution, actual hard crash behavior, Docker
ingress, IPv6, backup restore, or production readiness.

## Validation

```text
Focused Gate738Y + health + migration-lineage tests: 14 passed
Full pytest: 1014 passed, 23 skipped, 1 existing Starlette/httpx deprecation warning
Ruff on changed Python files: PASS (after removing one now-unused legacy import)
python -m compileall -q app tests: PASS
python -m alembic heads: 20261004_0033 (single head)
git diff --check: PASS (existing LF/CRLF working-copy warnings only)
```

Skip inventory (all reasons explicit):

| Skip reason | Count | Classification |
|---|---:|---|
| PostgreSQL environment not configured / explicit disposable PostgreSQL port or URL absent (exam concurrency, Gate735B, Gate736A, Gate738K, Gate738P guard matrix, Gate738E lifecycle/migration, Gate733 tenant context) | 19 | `ENVIRONMENT_REQUIRED`; no database qualification claimed. |
| Positive authorization cases duplicated by a separate acceptance test | 4 | `INTENTIONAL_TEST_CASE_SKIP`; acceptance coverage exists elsewhere. |

The Docker daemon being started does not itself provide the specifically named
disposable PostgreSQL URLs/ports or authorize any container operation. No
Docker commands, migration commands against a database, or database writes
were performed for Gate738Y.

## Risk and recommended resolution

Static lineage and orchestration checks pass. Before relying on the database
contract as runtime evidence, run the separately gated Gate738P PostgreSQL
qualification with its explicitly designated disposable database and named
candidate environment. Do not infer PostgreSQL lock, crash, ingress, or restore
behavior from this DB-free result.

## Mutation record

```text
Workspace changes: tests, qualification harness entrypoint guards, and docs only
Application business logic: NONE
Migration files/schema/data: NONE
Docker/container/network/volume: NONE
Staging/production: NONE
Environment/secrets: NONE
Commit/deploy: NONE
Frozen candidate manifests: untouched
```

## Verdict

```text
HARNESS_MODEL_MODERNIZED = PASS
DATABASE/RUNTIME QUALIFICATION = NOT RUN (explicit environment required)
GATE738Y = PASS
```
