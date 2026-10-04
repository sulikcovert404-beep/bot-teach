# Gate738L — Reopened Immutable Candidate Artifact Runtime Qualification

Date: 2026-10-04

## Current verdict

**ARTIFACT_QUALIFICATION_BLOCKED — HOST_PYC_BUILD_CONTEXT_CONTAMINATION**

Gate738L reopened after Commander accepted Gate738N dependency/runtime qualification and authorized requalification using that exact candidate. The reopened run stopped during frozen-artifact hygiene verification, before creating or changing Gate738L Docker resources. No repair was attempted because the candidate freeze explicitly forbids edits during qualification.

## Candidate freeze verified

- Worktree: `D:\project\ai-teacher-gate731-target`
- Branch: `codex/gate731-target`
- Base HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Source state: `UNCOMMITTED_CANDIDATE`
- Candidate image-input manifest SHA-256: `sha256:49bcac4f00e1d6643e4569c799acefa5b220bac9dbfdbacd5c09c4fe8a763d9b`
- Freeze manifest file SHA-256: `bb25bb9dd5f10f7ee474ca7ad1cea604d4226a0786826dc3c8a5af4e3f89a878`
- Dockerfile SHA-256: `4bb2ff74177a6c97c2c44b5aeefd7476c894d4af08f9cc7fac839a15b2d94045`
- pyproject.toml SHA-256: `eac92d268175c3fe88167336eac588530189cf84a7aa843e90ec3d908e3c86d3`
- Alembic heads: exactly one, `20261004_0032`
- Gate738M digest-pinned base remains unchanged: `docker.io/library/python:3.12-slim@sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`

No app, migration, dependency, Dockerfile, or `.dockerignore` changes were made during this reopened run.

## Candidate images and reproducibility evidence

| Image | Image ID | Created |
|---|---|---|
| `codex-gate738n-qualified-a-20261004` | `sha256:38285ebd56de395e92760aba8c9bd423beb0faeeb12a9f256ab5d0c69bed1bcd` | `2026-10-04T12:37:48.655996897Z` |
| `codex-gate738n-qualified-b-20261004` | `sha256:b8a64cae9442a58bb8bb86dd247c3991e6e552a8dda10942a19983bc2fda2a03` | `2026-10-04T12:39:46.085787043Z` |

Both images carry matching Gate738N, base HEAD, base-image digest, candidate-manifest SHA, and `UNCOMMITTED_CANDIDATE` labels. Both run Python `3.12.15` as `appuser`. The container-visible `pip freeze` outputs match (SHA-256 `338c7a5aebdd121bff576a0244370530cd0c5d1c2218d53f4da440331f49c06c`). A recursive content-hash inventory matched across all 13,106 files in each image; zero file-content hash rows differed. The rootfs has 12 layers; the first five layer digests match and later layer digests differ. The image `Created` timestamps differ. This confirms identical filesystem file bytes and dependency inventory, while the full OCI image IDs are distinct; byte-identical images are not claimed.

## Blocking evidence: host-generated Python bytecode is in the candidate

- Image A contains 380 `.pyc` files under `/app`; Image B also contains 380. Their filenames use the `cpython-313` cache tag.
- Both images themselves report Python `3.12.15`.
- The workspace interpreter is Python `3.13.14`.
- SHA-256 of `/app/app/api/routes/__pycache__/auth.cpython-313.pyc` in image A is `67a4fd28c56d8fc6c601000f579b30b156992cec3a7ba6d88c93f726c4c99141`, exactly matching the corresponding workspace `.pyc` file.
- The current `.dockerignore` contains `__pycache__` and `*.py[cod]`, but the frozen candidate still includes nested cache directories. This is direct evidence that workspace-generated Python 3.13 bytecode entered the image build context. The old cache bytecode is not suitable build input for the Python 3.12 artifact, even though the application import checks passed.

This violates Gate738L's explicit requirement that host-generated `__pycache__`/`*.pyc` files not contaminate the immutable artifact. It also means the exact Gate738N candidate must not proceed into the production-like topology, migration/drain/security matrices, or clean-run qualification. Candidate code and semantics remain untouched.

## Gate738L checks

- Candidate identity and labels: PASS.
- Python/dependency/source-payload identity: PASS.
- Host `.pyc` exclusion/build hygiene: **FAIL — blocker above**.
- Fresh Gate738L database, artifact topology, ingress, drain/fence, restart, old-writer-zero, adversarial privilege matrix, contract guard, dual clean runs: NOT RUN because the frozen candidate failed build-hygiene acceptance.
- Reopened-run migrations: NONE. The previous Gate738N disposable migration result remains Gate738N evidence only.
- Full workspace tests were not repeated in this reopened Gate738L run. Gate738N previously recorded `1003 passed, 14 skipped, 1 warning`; that result does not waive Gate738L's artifact acceptance checks.
- Production/Staging/SSH/registry/deploy/commit: NONE.
- Docker containers/networks/volumes: no Gate738L resources were created, removed, or changed in this reopened attempt. Existing Gate738L PostgreSQL/Redis containers were left as found. `ai-teacher-gate732-pg`, `mentor-bot`, `codesho_staging`, and other projects were untouched.

## Recommendation and decision required

Issue a narrowly scoped build-context hygiene Gate to exclude nested `__pycache__` directories and `*.py[cod]` recursively, regenerate the candidate manifest, rebuild two images, and verify that no host-generated bytecode is present. Then reopen Gate738L from Phase 0 against the new frozen candidate. Do not reuse the current Gate738N image tags for the full Gate738L qualification.

The repair was deliberately not made here because Gate738L requires the candidate to remain frozen and says to stop, report, and obtain a separate repair Gate when a defect appears.

## Reopened qualification addendum — Gate738O frozen candidate (2026-10-04)

### Current verdict

**GATE738L_INCOMPLETE** — the repaired Gate738O artifact passes the former bytecode-hygiene blocker and the quantitative SMALL/MEDIUM/STRESS lock matrix plus local functional/security evidence below are positive. A second fresh topology now has independent lock, ACL, compatibility, race, failure-atomicity, backend-termination, and ingress-health evidence. Gate738L remains incomplete because an in-flight crash/restart of the OLD API container and final scoped cleanup remain unqualified. IPv6 loopback ingress is also unavailable in this Docker Desktop environment.

### Candidate identity and hygiene

- Frozen Gate738O candidate manifest: `docs/GATE738O_CANDIDATE_FREEZE_MANIFEST.json`; SHA-256 `8d2c51327b66f77521db44a3013560f572cce573a6e6e55f3d90bbff0524b6dc`.
- Candidate identity recorded in the manifest: `sha256:bb5594121835be5a2af468e8ffd6508edb1e8b414d7b3b240ce6ab7a5bd54eb9`; all 403 inputs re-hashed without mismatch after build.
- Pinned base remains `python:3.12-slim@sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`.
- Qualified candidate A image ID: `sha256:fbf482cb7bfa5274b103b8fd1f7c144c822722bf8afd891da8706a9612f73dee`.
- Qualified candidate B image ID: `sha256:5ceac550efb43f225760ec738c668e7e8bdc71c72f402c137d828333cc87948f`.
- Both images have zero `.pyc`/`__pycache__` entries, matching application/dependency inventories, successful app import and `pip check`. The prior Gate738N bytecode contamination is repaired for this O candidate; no application, migration, dependency, or Dockerfile input changed during this qualification.

### Local production-like topology and writer control

- Gate-owned private network `codex-gate738l-o-net-20261004` is Docker-internal. PostgreSQL and Redis have no host-published ports. OLD and CANDIDATE API containers have no host-published ports. The only published application ingress is `127.0.0.1:18582` on the separate edge network `codex-gate738l-o-edge-20261004`.
- IPv4 ingress `/health` and `/health/ready`: HTTP 200. A host-direct request to the API backend was unavailable. PostgreSQL and Redis were healthy. IPv6 loopback ingress timed out.
- Fresh disposable topology database reached `20261004_0032`; API readiness was 200 with `app_runtime`. The role is neither SUPERUSER nor BYPASSRLS.
- Synthetic OLD write through ingress succeeded while OLD served. OLD was changed to DRAINING; active OLD writer transactions reached zero; a new OLD write failed without adding a row. Candidate writes remained successful. OLD was then changed to FENCED; the persistent state survived a container restart, OLD writes remained rejected, and candidate writes continued.
- A synthetic in-flight OLD transaction was observed in PostgreSQL. Graceful stop terminated the container; its transaction rolled back, active OLD transaction count returned to zero, and the fenced state survived restart. This demonstrates graceful termination behavior, not SIGKILL/hard-crash behavior.
- Gate738K PostgreSQL writer-admission suite: `3 passed`. Gate738H compatibility/race/contract/failure-atomicity harness: `PASS` on the isolated disposable PostgreSQL cluster using a helper sharing only that DB container's network namespace. The loopback-only Gate738E guard was preserved; no published DB port or guard bypass was used. It exercised 200 synthetic parent rows and reported zero missing current revisions, zero invalid reviews, 100 backfill-first and 100 writer-first race pairs, runtime wrong-tenant read denial, denied forbidden writes, candidate write success, contract refusal before validation, and atomic rollback to revision `20261003_0029` with no partial contract constraints.
- Source-level raw database connection inventory found the central SQLAlchemy engine/writer-admission hook in `app/db/base.py`, the intentionally loopback/disposable-only backfill worker in `scripts/backfill_submission_revisions.py`, and the developer benchmark in `scripts/pgvector_benchmark.py`. No other raw database connection entry point was found by this search. This is source inventory evidence, not proof against an unobserved external process.

### Workspace and artifact verification

- Full workspace test suite: `1003 passed, 14 skipped, 1 warning`.
- Ruff: `626` existing findings in `app migrations tests scripts`, matching the Gate738N recorded baseline; no Python source changes were made in the reopened run, so new Ruff findings are `0`.
- `python -m compileall -q app migrations`: PASS.
- Alembic heads: one head, `20261004_0032`.
- `git diff --check`: PASS. No commit, push, deploy, production/staging action, external service call, or real-user write occurred.

### Remaining Gate738L requirements

1. Second independent topology was created from fresh PostgreSQL/Redis/API/ingress resources and most qualification layers were repeated against the same immutable A/B artifacts; the old API in-flight container crash/restart sequence remains unqualified.
2. Quantitative SMALL/MEDIUM/STRESS matrix completed on the first disposable cluster: ACCESS EXCLUSIVE lock wait was 0ms for all three tiers; measured hold was 16.79ms / 31.04ms / 21.19ms. Reader max latency was 19.76ms / 38.33ms / 21.36ms with zero reader failures; writer max latency was 21.77ms / 37.24ms / 23.23ms and median 1.71ms / 1.75ms / 1.70ms with zero writer failures. Migration 0030 completed in 1440.40ms / 1629.39ms / 1454.08ms; all tiers reached 0030 and advanced through 0031 without migration error. The harness measured individual statement latency and lock wait/hold; explicit transaction-duration and deliberate timeout probes were added in run2 below. Lock mode was inferred from the ACCESS EXCLUSIVE rows queried by the harness.
3. Qualify an in-flight OLD API container crash/restart rollback case; PostgreSQL writer-backend termination passed, but is not equivalent to terminating and restarting that container.
4. Remaining work: perform the authorized in-flight OLD API container crash/restart qualification, then clean up only resources created with the `codex-gate738l-o-` prefix after retaining the final evidence. Existing `codex-gate738l-db-20261004`, `codex-gate738l-redis-20261004`, `ai-teacher-gate732-pg`, `mentor-bot`, `codesho_staging`, and every other project remain untouched.

### Mutation and privacy boundary

Only uniquely named disposable Gate738L resources were used. API/DB/Redis traffic used synthetic data and locally generated test-only values. No environment file or real secret was read or printed. No database outside the Gate-owned disposable cluster was accessed for writes. No migration, schema, or data change was made to an existing shared project. Gate-owned containers, networks, and volume are retained pending the remaining qualification/cleanup phase.

### Independent topology run 2 — initial partial snapshot (2026-10-04)

A second clean set of Gate-owned resources was created under the unique `codex-gate738l-o-r2-` prefix, using the same immutable A/B API images, a fresh PostgreSQL volume/database, fresh Redis, fresh internal/edge networks, and a separate ingress on `127.0.0.1:18583`.

- Fresh database migrated to `20261004_0032`; synthetic `app_runtime` verified `rolsuper=false`, `rolbypassrls=false`.
- Fresh Redis returned PONG. OLD and CANDIDATE `/health/ready` both returned HTTP 200. Both API containers had no published host ports; only the ingress published loopback 18583.
- Through ingress, OLD and CANDIDATE synthetic Telegram authentication writes returned HTTP 200 before drain.
- Operator control transitioned `legacy` through DRAINING to FENCED. A subsequent OLD write returned HTTP 500 and the synthetic user's row count remained zero; a CANDIDATE write returned HTTP 200 and its row count became one. PostgreSQL showed legacy FENCED and zero active legacy writer transactions.
- At the time of this original note, the second run was partial. The continuation below records the subsequently completed quantitative lock matrix, ACL/failure-atomicity audits, Gate738H integrated qualification, Gate738K writer-admission suite, and loopback health checks against this same fresh cluster. Docker-container crash/restart itself remains unqualified.

At this initial snapshot the dual complete-run criterion was OPEN. See the continued qualification below for the additional independent run2 results; current verdict remains **GATE738L_INCOMPLETE** only for the listed container crash/restart and cleanup gaps.


### Quantitative lock-matrix run — first disposable topology (2026-10-04)

The existing Gate738H matrix harness was executed from a temporary copy inside the Gate-owned loopback helper container, with its project root pointed to /app. It created uniquely named disposable databases on the Gate-owned PostgreSQL cluster, ran the same frozen migrations/backfill workload, and dropped each generated database in the harness finally path. Summary: SMALL 100 submissions/5 reviews, MEDIUM 1,000/50, STRESS 5,000/250; migration errors 0; reader failures 0; writer failures 0; ACCESS EXCLUSIVE observed wait 0ms; observed hold durations 16.79ms, 31.04ms, and 21.19ms respectively. No persistent Gate topology resource was changed by this matrix. Full measurements are recorded in the preceding checklist item. The initial attempt to stage the harness under read-only /app/tests was denied before execution; the corrected /tmp copy ran successfully. No DB remained from the failed attempt (the script's database cleanup ran).

### ACL and failure-atomicity evidence (first disposable topology, 2026-10-04)

- Gate738H ACL inventory completed on a uniquely named disposable database and was dropped by its harness. `app_runtime` was `NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEROLE`, `NOCREATEDB`, and `NOREPLICATION`; `public` schema `USAGE=true`, `CREATE=false`.
- 48 public relations were checked; no relation had unintended write or DDL grants. `student_submissions` and `submission_reviews` had forced RLS and runtime SELECT only in this inventory; `submission_revisions` had forced RLS and SELECT/INSERT only. Sensitive backfill/rollout state tables had no runtime table privileges. No runtime membership in other roles or default ACL entries were found. The catalog inventory reported expected SECURITY DEFINER functions as owner `postgres`, with pinned `search_path=pg_catalog`; the Gate738E bridge functions were not executable by app_runtime or PUBLIC.
- Gate738H failure-injection harness: PASS. Synthetic bridge failures before/after parent pointer and before/after revision insert returned SQLSTATE P0001 and rolled back parent/revision rows; failed review insert left review count unchanged. Migration 0030 mid-DDL injection left metadata at 0029 and created zero partial contract checks. Migration 0031 fence-before and fence-after injections left metadata at 0030 and rollout at COMPATIBILITY; after removing the test-only injection, 0031 succeeded.
- Both harnesses used only uniquely named disposable databases on the Gate-owned cluster; they dropped their databases in `finally`. No shared project database was targeted.
### Final workspace regression and static checks (2026-10-04)

- `python -m pytest -q`: **1003 passed, 14 skipped, 1 warning** in 30.89s. The warning is the installed Starlette/httpx TestClient deprecation notice.
- `python -m compileall -q app migrations`: PASS.
- `python -m alembic heads`: exactly one head, `20261004_0032`.
- `ruff check app migrations tests scripts`: 626 diagnostics, matching Gate738N's recorded pre-existing baseline; no Python source files changed during this Gate738L continuation. A broader `ruff check .` includes additional repository paths and was not used for the baseline comparison.
- `git diff --check -- docs/GATE738L_IMMUTABLE_CANDIDATE_ARTIFACT_RUNTIME_QUALIFICATION_RESULT.md`: PASS.
- Gate-owned loopback test query showed no leftover databases from the matrix/ACL/failure-injection harnesses. Persistent Gate738L topology containers remain retained for pending review; no non-Gate container was touched.

### Current disposition

The quantitative first-run lock matrix, ACL catalog audit, failure-atomicity harness, and full workspace regression now have current PASS evidence. The overall Gate remains **GATE738L_INCOMPLETE** because an in-flight crash/restart of the OLD API container and final scoped cleanup remain incomplete. No repair or production/staging mutation was attempted.
### Independent topology run 2 — continued qualification results (2026-10-04)

The previously partial run2 was advanced using the same immutable A/B images and fresh run2 cluster. Temporary test harness copies were kept under `/tmp` in a helper sharing only run2 PostgreSQL's network namespace; harness-only path adjustments pointed Alembic at `/app` and the exact frozen backfill script copy at `/tmp`. No frozen image or candidate input changed.

- Quantitative lock matrix completed on run2. SMALL / MEDIUM / STRESS were 100/1,000/5,000 submissions and all reached migration 0030 with no migration error. ACCESS EXCLUSIVE observed wait was 0ms at all sizes; hold was 13.27ms / 16.35ms / 16.22ms. Reader max latency was 17.65ms / 16.70ms / 18.27ms with zero failures; writer max latency was 17.30ms / 20.34ms / 21.53ms, median 1.68ms / 1.63ms / 1.62ms, zero failures. Migration 0030 elapsed 1353.77ms / 1387.34ms / 1373.33ms. The harness advances each DB through 0031 and drops it afterward.
- ACL audit on run2: 48 public relations checked; zero public write/DDL grant findings; runtime has no SUPERUSER/BYPASSRLS/CREATEROLE/CREATEDB/REPLICATION; no role membership/default ACL entry.
- Failure-injection harness on run2: PASS for bridge atomicity, 0030 mid-DDL rollback, 0031 fence-before/fence-after rollback, and successful 0031 after removing injected failure.
- Integrated Gate738H qualification on run2: PASS. It exercised 200 synthetic parents; 100 backfill-first and 100 writer-first races; 0029/0030 compatibility; 0031 legacy SQL denial with SQLSTATE 55000 and no parent/review mutation; candidate writes after contract; zero reader/writer failures; wrong-tenant read denied and update affecting zero rows; final integrity zero missing current revisions / invalid reviews; contracted rollout state. Final disposable DB head was 0031 and the DB was removed by the harness.
- Gate738K writer-admission PostgreSQL tests on run2: `3 passed`, including an uncommitted writer backend terminated with `pg_terminate_backend`, verified rollback and zero active writers, then verified fenced writes remained denied through a reconstructed writer factory. This tests abrupt PostgreSQL client-backend termination and durable application fence; it does not prove Docker container or PostgreSQL server restart behavior.
- IPv4 loopback ingress on both Gate topologies returned `/health=200` and `/health/ready=200`. Docker inspection confirmed only ingress published (`127.0.0.1:18583` on run2); both API containers had no published ports. API backends are attached only to the private Gate network, while ingress bridges private and edge networks. IPv6 was unavailable as already recorded.
- No harness DBs were left behind. Gate-owned run2 containers and volumes remain retained. No shared project container, network, volume, or database was targeted.

Run2 now has independent evidence for lock, compatibility, race, ACL, failure atomicity, backend termination, health, writer transaction duration, and deliberate lock-timeout behavior. The requirement for an actual old API container crash/restart while an in-flight writer exists remains open; no container stop/kill was performed in this continuation.
### Run2 transaction-duration and timeout probes (2026-10-04)

- A unique synthetic writer generation and user were created in the Gate-owned run2 database using the frozen writer-admission code. One transaction inserted the user, held for a 150ms synthetic database sleep, and committed. Observed wall duration was 167.89ms; the process-local completed-write metric recorded 155ms; active writer gauge returned to zero after check-in. The probe removed its unique synthetic user and generation row in `finally`.
- A second unique writer attempted an update while a synthetic transaction held `ACCESS EXCLUSIVE` on `student_submissions`, with `SET LOCAL lock_timeout='100ms'`. The actual writer path failed closed with PostgreSQL SQLSTATE `55P03` as expected; the lock was released and its unique synthetic user/generation were removed. This is an intentionally induced lock-timeout test, separate from the concurrent load matrix where no timeout occurred.
- One exploratory measurement attempt used an overlong writer instance identifier and was rejected by the Gate's identity validation before creating a user; transaction rollback left no generation or user row. The corrected measurement passed. No application/image changes were made.

The unresolved hard-crash requirement specifically means terminating/restarting the OLD API container with an in-flight writer and then proving rollback, zero admitted writers, persistent fence, and candidate continuity. PostgreSQL backend termination evidence exists, but does not substitute for that container-level test. Container termination was not run in this continuation.

### Commander closure decision and post-start resource audit (2026-10-04)

- Commander closed Gate738L with final verdict `CONTRACT_GUARD_BLOCKED`; the frozen Gate738O artifact is `NOT QUALIFIED`. This is a design blocker: migrations 0030/0031 contract before the 0032 writer-generation control table exists and do not enforce all required rollout preconditions.
- Docker Engine was subsequently observed running as Docker Desktop 29.5.3. Read-only inventory found Gate-named containers still running under exact names `codex-gate738l-*` / `codex-gate738l-o-*`; no commands were issued to stop, restart, remove, or alter containers, networks, volumes, or images.
- Provenance reconciles: the running Gate738O-labeled API/runner containers report `io.ai-teacher.candidate-manifest-sha256=sha256:bb5594121835be5a2af468e8ffd6508edb1e8b414d7b3b240ce6ab7a5bd54eb9`, which equals the `candidate_image_manifest_sha256` field in the frozen Gate738O manifest. The manifest file's own envelope SHA-256 is `8d2c51327b66f77521db44a3013560f572cce573a6e6e55f3d90bbff0524b6dc`; these are distinct, explicitly represented digests, not a mismatch. The OLD/CANDIDATE image IDs also match the recorded IDs.
- Read-only inventory attributed the exact `codex-gate738l-*` containers, five Gate-named networks, three Gate-named PostgreSQL volumes, and three anonymous Redis volumes to Gate738L. Each Redis volume was mounted only by its corresponding exact Gate738L Redis container.
- No `ai-teacher-gate732-pg`, `mentor-bot`, or `codesho_staging` resource was targeted. Gate738P work must use a new, separately named disposable topology and a newly qualified candidate; the Gate738L candidate remains retired.
- Commander-authorized exact cleanup completed: the 15 inventoried Gate738L containers, all five Gate738L networks, all three Gate738L PostgreSQL volumes, and all three corresponding Redis volumes were removed by exact name/ID. No prune, wildcard, image removal, or other-project resource operation was run. A post-cleanup inventory found no remaining `codex-gate738l` containers, networks, or named volumes.

Final Gate738L verdict: `CONTRACT_GUARD_BLOCKED` / `NOT QUALIFIED`.

### Runtime writer-path inventory and live configuration recheck (2026-10-04)

- A fresh source scan found the only SQLAlchemy engine construction in `app/db/base.py`. Runtime API routes obtain sessions through `app/api/routes/auth.py:get_session`, which passes the configured writer-admission flag, generation, and instance identity into the shared `build_session_factory`. The application's lifespan factory in `app/main.py` uses that same factory. Route and service ORM writes (`session.add`, ORM DML, and `Session.execute`) therefore converge on the shared engine's DML admission hook; no separate runtime SQLAlchemy engine construction was found.
- The only direct `asyncpg.connect` source found is `scripts/backfill_submission_revisions.py`, classified as `NON-RUNTIME / DISPOSABLE-ONLY`: the script validates the disposable Gate database identity before connecting. `scripts/pgvector_benchmark.py` is a developer benchmark using the shared session factory, classified `TEST-ONLY / DISPOSABLE FIXTURES`. Backup/restore PowerShell scripts are operator workflows, not application runtime writers. No `psycopg.connect` or additional direct PostgreSQL connection path was found under `app/` or `scripts/`.
- Live read-only configuration probes in both run2 API containers confirmed image IDs remain OLD `sha256:fbf482cb7bfa5274b103b8fd1f7c144c822722bf8afd891da8706a9612f73dee` and CANDIDATE `sha256:5ceac550efb43f225760ec738c668e7e8bdc71c72f402c137d828333cc87948f`; both report `writer_admission_enabled=True` (`legacy/oldr2` and `candidate/newr2`, respectively). Docker inspection showed neither API container has host-published ports. No environment values or secrets were printed.
- Classification: API ORM/Core DML = `CENTRAL ADMISSION CONTROLLED`; DB fence trigger = `DB FENCE/TRIGGER GUARDED`; backfill script = `NON-RUNTIME / DISPOSABLE-ONLY`; benchmark and qualification harnesses = `TEST-ONLY`; migration DDL = `MIGRATION-ONLY`. This is a repository source/configuration inventory and live check of these two containers; it does not claim to prove absence of an external writer process outside this isolated topology.
- A no-row runtime adversarial probe on the Gate-owned run2 CANDIDATE attempted direct `UPDATE` against a deliberately nonexistent generation and then called the transition helper for `legacy → SERVING`. Both were denied with PostgreSQL SQLSTATE `42501`; the first targeted no matching row even if permissions had allowed it. This confirms the real `app_runtime` identity cannot directly alter drain state or invoke the helper to self-unfence. No control-state row was modified.

### Contract precondition integration audit (2026-10-04)

- The Gate738L-required release contract guard matrix is **BLOCKED by a missing integration guard**, not merely untested. Static inspection of migration `20261003_0030_submission_revision_contract.py` shows its machine guard checks only `submission_revision_backfill_state.status = 'VALIDATED'`. Migration `20261003_0031_submission_revision_compat_cleanup.py` checks only that one rollout-state row is `COMPATIBILITY` before changing it to `CONTRACTED`.
- Neither contract migration, the migration qualification scripts, nor the application contains a guard that ties contract execution to all required release preconditions: OLD generation `FENCED`, active OLD writers = 0, OLD-generation write transactions = 0, no other OLD writer instance, and candidate eligible/healthy. Repository search found writer-state reads in `app/services/writer_admission.py` and its Gate738K harness, but no call/reference from migrations `0030`/`0031` or a contract orchestration entry point.
- Gate738L requires these conditions to be enforced machine-readably and rejects operator-memory-only gating. Testing the existing `VALIDATED` and `COMPATIBILITY` checks does not satisfy that requirement. With the candidate frozen, no repair was made; this Gate cannot receive a passing contract-guard result without a separately authorized control-plane change or an already-existing guard being identified.
- Consequence: classify `CONTRACT_GUARD_BLOCKED`. Preserve the artifact and disposable evidence; do not run a real rollout contract or modify candidate semantics in Gate738L.

### Candidate restart persistence probe — independent run 2 (2026-10-04)

- Precondition read from the Gate-owned disposable `ait_gate738l_r2` database: `legacy=FENCED`, `candidate=SERVING`. The candidate container was the frozen image B (`sha256:5ceac550efb43f225760ec738c668e7e8bdc71c72f402c137d828333cc87948f`); OLD remained running on frozen image A.
- Per the Gate's distinct candidate-restart criterion, only `codex-gate738l-o-r2-candidate-20261004` was manually restarted. No OLD or shared-project container was stopped, killed, or restarted. Container returned to `running` on the same image. Docker's automatic `RestartCount` remained 0 (manual restart is not a policy-triggered restart).
- The loopback ingress briefly returned connection errors during startup. On the next check five seconds later, `/health` and `/health/ready` both returned HTTP 200; readiness still reported Alembic head `20261004_0032`.
- After restart, a Telegram auth request signed inside the candidate process using its configured token created one uniquely identified synthetic user and returned HTTP 200 / `STUDENT`. The token and JWT were not printed. DB control state remained `candidate=SERVING`, `legacy=FENCED`.
- Exact cleanup was attempted without weakening controls: direct administrative DELETE was rejected by the writer-generation fence; DELETE through the app's `app_runtime` session was rejected for lack of table privilege. The synthetic row (telegram_user_id `1791123902167`) remains isolated in this Gate-owned disposable database and is included in the retained-resource inventory for eventual exact Gate cleanup. No grants, trigger changes, or fence bypass were attempted.
- Result: candidate restart persistence and resumed candidate write path **PASS**; normal readiness **PASS after startup**. This does not qualify the still-open hard-crash of OLD with an in-flight transaction, nor does it clear the independent **CONTRACT_GUARD_BLOCKED** finding. Candidate/image identity is unchanged.

#### Contract-guard sequencing evidence (read-only source audit, 2026-10-04)

- Alembic history and source establish the sequence `0030 -> 0024 -> 0025 -> 0026 -> 0031 -> 0032`. Revision `0032` is the first migration that creates `ai_teacher_writer_generation_state` and initializes `legacy=SERVING`; its `down_revision` is `0031`. Therefore neither `0030` nor `0031` can query the Gate738K generation table at execution time: that table does not exist until after both contract revisions have run.
- `docker-compose.yml` defines the `migrate` service as `alembic upgrade "$EXPECTED_MIGRATION_HEAD"` using a PostgreSQL owner URL. No machine-readable drain/zero-writer preflight appears in that migration command or an adjacent migration orchestration wrapper found by repository-wide search.
- This confirms the gap is structural in the frozen artifact, not just a missing test case: the current migration path can contract before the persistent writer-generation control table is created. No schema, migration, Dockerfile, compose, or application edit was made; no migration was run.
- Updated classification remains `CONTRACT_GUARD_BLOCKED`; candidate remains frozen. Resolution requires an explicitly authorized separate design/implementation Gate for pre-contract orchestration or a revised release sequence, then a new candidate qualification. This recommendation does not authorize that change.

### Gate738L reopened from Phase 0 on Gate738P candidate (2026-10-04)

Commander accepted Gate738P and authorized a fresh Gate738L Phase 0 against its candidate manifest. This section supersedes the earlier Gate738L candidate's retirement only for the new candidate; the historical `CONTRACT_GUARD_BLOCKED` verdict above remains valid for the retired Gate738O artifact.

- Candidate manifest SHA-256 recomputed as `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1`; all 407 listed source/context file hashes match. The local image ID matches the manifest: `sha256:d3c95ece976ca6425b5fc5ee6b2b93cb73f0d1bea868e264de6fa0c0ef318fe2` (`linux/amd64`). No rebuild or image mutation was performed.
- Docker Desktop Engine `29.5.3` responds. Initial `docker ps -a` inventory showed no running containers. The protected `ai-teacher-gate732-pg` container and multiple unrelated stopped project containers/networks/volumes were observed read-only and left untouched.
- Attempt to create the exact, loopback-bound Gate738L disposable PostgreSQL container was rejected by the command execution policy (`blocked by policy`) before execution. Follow-up read-only inventory confirmed the intended Gate738L run-1 container, volume, and network were not created. No alternate execution route was used.
- Non-container workspace regression: `1005 passed, 23 skipped, 1 existing Starlette/httpx deprecation warning` in 30.44 seconds. Ruff on the Gate738P runtime/guard modules passed. The focused PostgreSQL contract/admission tests reported `2 passed, 12 skipped`; the skipped cases require an explicitly named local disposable PostgreSQL URL, so they do not qualify the database-backed Gate criteria.

Current status: `GATE738L_PHASE0_BLOCKED_AT_DISPOSABLE_DOCKER_PROVISIONING`. The new artifact identity checks pass, but no Gate738L crash/restart or staged migration execution has occurred in this reopened run. This is not a Gate738L pass or final verdict. Required next condition is an allowed execution path for the authorized exact disposable Docker/PostgreSQL resources; protected and unrelated projects must remain untouched.

Mutations in this reopened run: workspace test cache only; no Docker container/network/volume created, no database migration run, no image rebuilt, no production/staging/SSH/deploy/commit action.

### Final Commander disposition — reopened Gate738L Phase 0 (2026-10-04)

- Commander reviewed the disposable-Docker provisioning policy refusal and confirmed that no Linux Docker host can be provisioned from this environment. The Gate must close rather than remain suspended; no alternate route or policy workaround is authorized.
- Final verdict for the reopened Gate738L run: `CRASH_QUALIFICATION_ENV_BLOCKED`; final status: `NOT QUALIFIED`. Gate738P remains accepted as `PASS`, unchanged. The frozen Gate738P candidate manifest `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1` is `FROZEN / NOT REJECTED`.
- The blocker is qualification-environment availability, not a newly demonstrated candidate defect. Immutable artifact/runtime qualification, staged migration, and hard-crash validation were not completed in this run. The legacy Gate738H harness remains deferred and fail-closed.
- Production and staging remain `NO-GO`. No cleanup, migration, deploy, restart, or other Docker mutation was performed in the reopened run; the protected/shared inventory remained untouched.
