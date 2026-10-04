# Gate737A — Release Compatibility & Production Provenance Readiness

**Gate:** 737A  
**Scope:** read-only candidate/runtime qualification; no commit, build, deploy, migration, or production runtime mutation.

## Verdict

**PROVENANCE_BLOCKED**

The candidate migration chain is compatible by ancestry with the observed production revision, and backup archive integrity is verified. Release readiness is not established: the current production container's deployment invocation and CI/build-to-release chain are unknown, and its observed compose inventory/configuration does not match the running container metadata. The retired legacy classroom-membership endpoint is a security-required breaking change; external consumers have not been verified.

## Candidate freeze manifest

- Base HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Branch: `codex/gate731-target`
- Worktree: `D:\project\ai-teacher-gate731-target`
- Pre-report candidate changes: 43 paths (11 modified tracked files, 32 new/untracked files); preserved as-is.
- Candidate migration target: `20261003_0026`
- Local Alembic head: `20261003_0026` (single head at qualification time).
- Gate737A report is excluded from its own manifest to avoid a self-referential hash. No candidate files were modified by this report.

The manifest below records each candidate file's current SHA-256 and origin classification. `modified` means an existing tracked file changed in the worktree; `new Gate file` means untracked candidate implementation, test, migration, or prior Gate evidence; the two backup scripts are exact restored Git blobs from the separately qualified canonical backup commit `46f7aa...`.

| Path | Status | SHA-256 | Origin |
|---|---|---|---|
| `app/api/routes/student.py` | modified | `a49d2bea294bb28dfcf97878fe9bb4ebecaee365698f053c8686b2ee89bc2c61` | existing tracked file modified |
| `app/api/routes/teacher.py` | modified | `7e377d01513ade7ddd226d0cfbdff8c6785ebddc37dbc39dd023668c87abeafb` | existing tracked file modified |
| `app/db/models.py` | modified | `053ecc2c4eefe93084abeb7b7a93f645076a4a84fc408e385e6a8bceb9c19dd0` | existing tracked file modified |
| `app/main.py` | modified | `a6d787b26b2feac5fd8ab47e09fc916abd84f562817e54df34f5129cef5d6044` | existing tracked file modified |
| `tests/test_gate725_process_isolated.py` | modified | `52b20d28e5e05eeb79f505f27222c32f51dc26c41d21edbd62e7808d53f71df5` | existing tracked file modified |
| `tests/test_health.py` | modified | `7c1a3505a6735e3ce58794dbcf546ac257edbf0861d2db89593dc4402d5b44fc` | existing tracked file modified |
| `tests/test_migration_roundtrip_qualification.py` | modified | `51ccbdb31782c4156113e80cb200485ecc91e0c1ec5f24b1ca7d197f8330d6a5` | existing tracked file modified |
| `tests/test_multi_role_dashboard_authorization_contract.py` | modified | `1b594db3f41e06d420ecbcac7c9eb4dc096113df08c1e3e61ac55444a8611484` | existing tracked file modified |
| `tests/test_mvp_pilot_http_lesson_access.py` | modified | `78c7c926b24d8bbfe46f3f08912babcf220ff63bf02beed1df4d08f2e4c284bd` | existing tracked file modified |
| `tests/test_telegram_route.py` | modified | `0b10d688874ab88cc8134f826f2ce9eacadeb78e1122bc3ae1a7e447398b663e` | existing tracked file modified |
| `tests/test_test_identity_provisioning.py` | modified | `c46bd0ed19edb0e8deb23bb5a4df10529ff19e92ce0c46edf957264bc4c5c6b0` | existing tracked file modified |
| `app/api/routes/class_enrollment.py` | new | `c98dd9fc4045df38e54455aa420970a90668c646eae78440282851c04e350f24` | new Gate implementation/test/migration file |
| `app/api/routes/tenant_memberships.py` | new | `692ddd9c822265e8f0a94634ec84c3fd2341e0ec07ebdbc4fa00f03bbc54dd68` | new Gate implementation/test/migration file |
| `app/security/tenant_context.py` | new | `2a3e78cc37f7ca9b8749b660146f47bb053b5a88970abd81c3f245198ec38999` | new Gate implementation/test/migration file |
| `app/services/class_enrollment.py` | new | `21b3bc8f65d6a5b7a6eac89c729ff8318664756c6c20aeaa0d001ad2d7c0aaf6` | new Gate implementation/test/migration file |
| `app/services/submission_revisions.py` | new | `3d62a341e1c9aa7cc22dc4cfab3e665afe00f9d5746aed77697479a17edbc9dc` | new Gate implementation/test/migration file |
| `app/services/tenant_membership.py` | new | `888d808e2f45dec5ba330376ef20c9d6a62c8a2b2fe385e6d3e1720b113e9d83` | new Gate implementation/test/migration file |
| `docs/GATE731N_TARGET_BASE_RESTORATION_RESULT.md` | new | `159c2f58d56d185c2177b3442036b3a12d2ea078987fe6eadf210c73375d20bb` | new Gate evidence/report file |
| `docs/GATE732N_IMPLEMENTATION_RESULT.md` | new | `2eba951fafad56fd2bf35ba8a0e9c61ebaf61b9927627fe11da4066c2f8ec11b` | new Gate evidence/report file |
| `docs/GATE732N_IMPLEMENTATION_START_REPORT.md` | new | `d10838f2817a37373875f1ede026c93bd4a09fe26970d94d5d088b9523045e01` | new Gate evidence/report file |
| `docs/GATE732N_REVISION_SUBMISSION_FOUNDATION_REQUALIFICATION_RESULT.md` | new | `00fd4a2f7bca6d4b91e589cc48a9c9a05554bab52aa80875dbd28e77e1ac739f` | new Gate evidence/report file |
| `docs/GATE733A_CANONICAL_TENANT_CONTEXT_FOUNDATION_RESULT.md` | new | `6c131d2364f6145b564c95ac3b210028551d2d6cc73ef2ba2e3ecf810238e3a4` | new Gate evidence/report file |
| `docs/GATE734A_TENANT_MEMBERSHIP_PROVISIONING_RESULT.md` | new | `903290e9e89c198030a59f2b087a7c497974716ae45118d5ce53915fdf949a8c` | new Gate evidence/report file |
| `docs/GATE734B_DISPOSABLE_MEMBERSHIP_PROVISIONING_QUALIFICATION_RESULT.md` | new | `80b47b93634c75a20c5ff4ba893f3dd09bc65aa679e34226941b3fc4a1fc35c8` | new Gate evidence/report file |
| `docs/GATE735A_CLASS_ENROLLMENT_RESULT.md` | new | `7348e0e76d01c40dcd1df3d40c2984f3f8dd4050f51d7b96f57ab722f04c6ccb` | new Gate evidence/report file |
| `docs/GATE735B_SECURE_CLASS_ENROLLMENT_RESULT.md` | new | `8edafa818489318b23439699046ee8f782d1b4e6638c1f31a7cd2730ac20d69c` | new Gate evidence/report file |
| `docs/GATE736A_INTEGRATED_LOCAL_RELEASE_CANDIDATE_QUALIFICATION_RESULT.md` | new | `634ddd3e82e64efbb307e883e95abfda54b29324c591e7d4e6eddfdf68b49d3d` | new Gate evidence/report file |
| `docs/GATE736B_REGRESSION_HARNESS_STABILIZATION_RESULT.md` | new | `875cdf8776dfc4ad72e2c940c9df50a42a798b5d11ad281d7fa4252efca85d22` | new Gate evidence/report file |
| `migrations/versions/20260921_0022_provisioning_idempotency.py` | new | `cfe5045c895894469f953ce2c3bdb9fc61713dd8d99261fd5c5a216a40bd47c6` | new Gate implementation/test/migration file |
| `migrations/versions/20260924_0023_submission_revisions.py` | new | `79132ca63ed00786921be8a04c6313d9f508c9ddb57b5e4f02fb3faed538eeaf` | new Gate implementation/test/migration file |
| `migrations/versions/20261003_0024_canonical_tenant_context.py` | new | `2a4eb80eaf0e8ee49c193459e8efc92d1ccfea55f7b5443da6113f50805158b6` | new Gate implementation/test/migration file |
| `migrations/versions/20261003_0025_tenant_membership_provisioning.py` | new | `dd0eaa335121167a348e023b0270b98955f679f54a30b5284db8679ff9c6974b` | new Gate implementation/test/migration file |
| `migrations/versions/20261003_0026_class_enrollment_operations.py` | new | `a84e75a1b664df71a807719988ed3175be351a166b3b93740c66fe95d6eaa5f4` | new Gate implementation/test/migration file |
| `scripts/postgresql_backup.py` | new | `4b4273ea3df0feb7890e3b2b45d0689623b17c1621f16e36bc642c7b554a2204` | exact restored canonical Git blob (commit 46f7aa...) |
| `scripts/r2_offsite_packager.py` | new | `583d1ed3e7834ffab719c9f2e26deda3052e47adecd4fc350e43de11c167c3e6` | exact restored canonical Git blob (commit 46f7aa...) |
| `tests/conftest.py` | new | `8b4b37e802c54f2b7e30dd623abbe6724741dfcbedec5c182ab152f56c51867b` | new Gate implementation/test/migration file |
| `tests/test_gate735b_class_enrollment_postgres.py` | new | `af5c572afef81e2449557b0de546820998297c059a2bbb0b76c9f20f3b5cb8fb` | new Gate implementation/test/migration file |
| `tests/test_gate736a_integrated_candidate_postgres.py` | new | `07f0669fbf15e9ac659b060a495de433066de8a0cecbcb21e700bdafa337160f` | new Gate implementation/test/migration file |
| `tests/test_inmemory_rate_limit_app_isolation.py` | new | `a38e707c89d6ab7db5637e6a7d2a9edda5f1b4cb0ef5c505c6a1e4ab999ea809` | new Gate implementation/test/migration file |
| `tests/test_legacy_tenant_membership_boundary.py` | new | `98d249588b3634996c5240c1be1156a11d4aff005f28bf30208f4af4e3bc7f57` | new Gate implementation/test/migration file |
| `tests/test_submission_revision_lifecycle.py` | new | `aa6e3ddc8350ac17798b450ee284a2812a7c6a117e9efeebf6791fdf0dd325c7` | new Gate implementation/test/migration file |
| `tests/test_submission_revision_migration.py` | new | `b25c02533ed3e61b464e05f89aee1b05ef0f1ef4cc365d00dd910ce6edca5d6c` | new Gate implementation/test/migration file |
| `tests/test_tenant_context_foundation_postgres.py` | new | `a7636168109d6dedae8385346d668b082d8e2ffca9dce0c8c1e4f404a95fc9ce` | new Gate implementation/test/migration file |
## Migration lineage

| Revision | Parent | Result |
|---|---|---|
| `20260921_0022` | `20260912_0021` | Repository migration present; the running API's verified health implementation checks the database revision against its expected value. |
| `20260924_0023` | `20260921_0022` | Present in candidate chain. |
| `20261003_0024` | `20260924_0023` | Present in candidate chain. |
| `20261003_0025` | `20261003_0024` | Present in candidate chain. |
| `20261003_0026` | `20261003_0025` | Candidate target and local sole head. |

Production readiness response reports `migration_head=20260921_0022`; the OCI revision label identifies source commit `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`, which is present in the repository and contains the 0022 migration with parent `20260912_0021`. This provides a continuous candidate ancestry from the observed production revision to 0026. No migration command or database write was run. The revision observation is supported by the running image's inspected health-handler source, which queries `alembic_version` and reports the expected revision only when they match.

## API compatibility inventory

| Change | Classification | Evidence / remaining uncertainty |
|---|---|---|
| `POST /api/v1/teacher/v2/classrooms/{classroom_id}/members` retired and returns HTTP 410 | `SECURITY_REQUIRED_BREAK` + `UNKNOWN_EXTERNAL_DEPENDENCY` | Candidate tests cover the retired boundary. No active caller was found in the repository; external clients were not inventoried, so external dependency remains unknown. |
| Other Gate732–736 endpoint changes | `NON_BREAKING` or `CONTROLLED_BREAK` where documented in the corresponding Gate result artifacts | No additional retired route was identified by the candidate reports reviewed for this gate. |

No unknown internal caller was identified in the checked repository. The absence of an in-repository caller does not establish that external consumers do not exist.

## Production runtime provenance (read-only)

- Target: `92.118.190.101`; hostname `hamicard`; SSH identity `teacherstudent`; noninteractive sudo boundary verified as root.
- Docker compose inventory reports project `ai-teacher-staging`, two services, config file `/opt/apps/ai-teacher/release-local-rc-2026-09-17/docker-compose.yml`.
- Running API container: `ai-teacher-staging-api-1`; image `ghcr.io/sulikcovert404-beep/bot-teach`; image ID / RepoDigest `sha256:9fa6fd7e95626bf2c60fb6a1dd1e13f64620eb50b0e7be9ea9ee90a92d24c462`; created `2026-09-22T09:48:58.592830917Z`; restart count 0.
- OCI revision label: `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`, present in the repository. OCI `working_dir` and Docker `com.docker.compose.project.config_files` labels are empty.
- The inventoried compose definition uses `build: .` and declares a Docker healthcheck, while the live API is a registry image and Docker reports no API healthcheck. Compose inventory says `running(2)` while three `ai-teacher-staging` containers (API, PostgreSQL, Redis) were observed running. These are provenance/configuration contradictions, not instructions to reconcile them.
- Provenance chain: Git commit -> source repository **VERIFIED**; source commit -> running OCI revision label **VERIFIED**; CI/build definition -> image **UNKNOWN**; registry digest -> release artifact **UNKNOWN**; release artifact -> deploy invocation **UNKNOWN**; deploy invocation -> current container/compose configuration **CONTRADICTED / UNKNOWN**.
- Container origin classification: **still unknown** among manually created, older/different compose invocation, release-tool generated, or orphan/reconciled runtime. No recreation was attempted.
- `/etc/apps/ai-teacher/staging.env` metadata only: `root:root`, mode `0600`, size 1048 bytes. Values were not read or printed.
- Other observed projects, including `codesho_staging`, were left untouched.

## Backup, restore and rollback readiness

- Gate716N was assumed qualified per the issuing decision. On-host evidence shows the AI Teacher backup timer enabled and active/waiting; latest oneshot result successful (exit 0, `2026-10-03T03:34:44` as reported by systemd).
- Latest archive: `/opt/apps/ai-teacher/backups/20261003T000444Z/education.dump`, 197132 bytes. Manifest SHA-256 `8b914b72a778d65146817fd8b4b6e3a686202df8377013e1042c8991a4efe2ab` matched a fresh hash of the archive. Manifest timestamp: `20261003T000444Z`. No separate `.sha256` sidecar was found in the inspected backup locations; the checksum is present and verified in the manifest.
- A read-only `pg_restore --list` attempt through the existing DB container returned no listing entries (the host account could not access the Docker socket in the first attempt; the privileged retry yielded an empty listing count without a trustworthy command exit status). Therefore restore-listing verification for this latest archive is **UNKNOWN**, not PASS. No restore was performed.
- Current running image digest and source revision are identifiable, but qualification/pullability as a previous release artifact was not independently proven in this gate. Application rollback readiness: **PARTIAL / UNKNOWN**. Database rollback is not proposed; recovery must remain restore-based and separately authorized.

## Health and storage observations

- API `http://127.0.0.1:8000/health` and `/health/ready`: HTTP 200.
- Public `http://92.118.190.101:8000/health` and `/health/ready`: HTTP 200; no 502 observed.
- Readiness reported `status=ready`, `migration_head=20260921_0022`.
- Filesystem for `/` and `/opt/apps/ai-teacher`: ext4, 58G total, 28G used, 30G available (48%); inode use 10%.
- I/O pressure averages were 0.00 at 10/60/300 seconds in the observed snapshot; no storage anomaly observed.

## Release preconditions matrix

| Preconditions | Status | Notes |
|---|---|---|
| Candidate freeze manifest complete | PASS | 43 pre-report paths enumerated with SHA-256. |
| Migration lineage compatible | PASS (read-only) | Production 0022 is the candidate chain ancestor; target is explicit 0026. Migration remains unrun. |
| Breaking APIs classified | PASS WITH OPEN DEPENDENCY | Legacy route is a security-required break; external consumers remain unknown. |
| No unknown critical internal caller | PASS, repository scope | External caller inventory remains unavailable. |
| Current production revision known | SUPPORTED | Readiness response says 0022; verified handler compares DB `alembic_version`. |
| Explicit migration path | PASS (plan only) | 0022 -> 0023 -> 0024 -> 0025 -> 0026. |
| Runtime provenance reconstructed or safe replacement plan | BLOCKED | CI/build/release/deploy links and actual container origin remain unknown; compose/runtime discrepancies unresolved. |
| Backup/checksum readiness | PASS | Latest archive SHA-256 matched manifest. |
| Restore-listing readiness | UNKNOWN | Latest archive listing could not be validated with a trustworthy exit status in this gate. |
| Application rollback readiness | UNKNOWN | Current image digest known; prior qualified/pullable release not proven. |
| Destructive unresolved blocker | NONE OBSERVED | No destructive operation was attempted or recommended. |
| Production mutation | NONE | Read-only observations only. |

## Finding and recommended resolution

**Finding:** Candidate migration ancestry and latest backup integrity are supported. Production runtime identity is only partially reconstructed: image digest and OCI source revision are known, but build/release/deploy provenance is missing and compose/runtime inventory conflicts. The endpoint retirement also has an unverified external-consumer boundary. Restore listing and qualified application rollback are not proven in this gate.

**Risk:** A later release could package a correct candidate but cannot yet demonstrate that its build artifact and deployment path correspond to the currently running service. External clients may depend on the intentionally retired route. Recovery readiness also lacks current restore-listing and prior qualified rollback evidence.

**Recommended resolution:** Keep production frozen. For a separate read-only qualification, obtain authoritative CI/build and release-manifest evidence linking commit `77c3bbce...` to the running digest and the current deploy invocation; reconcile the compose inventory discrepancy from evidence without changing runtime; verify the latest dump with a trusted `pg_restore --list` exit status; identify a previously qualified application rollback image; and inventory/approve external consumers of the retired route. Then submit the complete release plan for a later explicit Release Gate. No commit, image build, migration, or deploy is authorized by this result.

**Confidence:** High for observed host/container/digest/HTTP/filesystem/backup-manifest facts; high for local migration ancestry; medium for production DB revision because it is derived through the verified readiness handler; low/unknown for deployment invocation, CI/build linkage, external API consumers, and rollback qualification.

## Mutations

`NONE` — no production or database mutation, migration, image build/pull, service/container action, or commit was performed.

**Next action:** `PROVENANCE_BLOCKED`; continue only under a separately scoped read-only evidence/recovery-readiness gate. Passing this gate would not constitute deploy approval.

