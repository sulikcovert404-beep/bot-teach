# Gate737B — Release Evidence Closure

**Mode:** Read-only evidence qualification  
**Verdict:** `PROVENANCE_BLOCKED` — `RELEASE PREP NOT READY`  
**Production/runtime mutations:** None

## Finding

CI-to-image provenance and structural backup validation are evidenced. The running API image digest matches the CI provenance artifact, but its runtime creation path is not fully attributable: the API container lacks Docker Compose project/config/working-directory labels while the database and Redis containers carry them. A usable rollback image and the external compatibility boundary are not qualified. The evidence set therefore does not close release readiness.

## A. CI/build to image provenance

**Status: PASS for the identified image.**

- Repository: `https://github.com/sulikcovert404-beep/bot-teach`
- Commit: `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`
- Workflow run: [35588891399](https://github.com/sulikcovert404-beep/bot-teach/actions/runs/35588891399), push on `master`, completed successfully on 2026-09-21.
- The run's `docker` job reports successful build, provenance generation, image attestation, and provenance artifact upload steps.
- The retained `release-provenance` artifact identifies `ghcr.io/sulikcovert404-beep/bot-teach`, the commit above, `linux/amd64`, and digest `sha256:9fa6fd7e95626bf2c60fb6a1dd1e13f64620eb50b0e7be9ea9ee90a92d24c462`.
- The artifact's `timestamp` is null and `attestation_reference` remains the literal placeholder `pending-after-attestation`; the successful CI attestation step is separate evidence, but the artifact itself is not a completed attestation reference.
- A second run, 35588089736, built from the same SHA and passed CI/staging smoke, but its Docker build ran on a non-master event and its provenance/attestation/artifact-upload steps were skipped. It is not the release-provenance source.

## B. Release/deploy to current container provenance

**Status: PARTIAL; digest/commit match, runtime invocation unknown.**

- Server: `hamicard`; Docker project inventory reports `ai-teacher-staging` with two Compose services and config file `/opt/apps/ai-teacher/release-local-rc-2026-09-17/docker-compose.yml`.
- Running containers include API, PostgreSQL, and Redis. All are running; PostgreSQL and Redis report healthy; API has no Docker healthcheck; restart count is zero for all three.
- API image reference and image ID: `ghcr.io/sulikcovert404-beep/bot-teach@sha256:9fa6fd7e95626bf2c60fb6a1dd1e13f64620eb50b0e7be9ea9ee90a92d24c462`. OCI revision label is `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`, matching the CI artifact.
- API was created and started at `2026-09-22T09:48:58Z`, after the CI artifact was produced. The latest two repeated inspections of container ID `951c474bc53203909ae152ae46024a5b82578955b8a7b24b0e3f4e4f1c6d5a69` returned `com.docker.compose.project=ai-teacher-staging` and `com.docker.compose.service=api`, plus OCI labels. They did not return Compose config-file, working-directory, or environment-file labels. The API has no mounts and is attached to `ai-teacher-staging_default`.
- PostgreSQL and Redis do carry Compose labels naming project `ai-teacher-staging`, config file `/opt/apps/ai-teacher/release-local-rc-2026-09-17/docker-compose.yml`, working directory `/opt/apps/ai-teacher/release-local-rc-2026-09-17`, and env-file path `/etc/apps/ai-teacher/staging.env`.
- The env file was not read. Previously observed metadata is root-owned mode `0600`, size 1048 bytes.
- Current local health checks returned HTTP 200 for `/health` and `/health/ready`.
- **Attribution contradiction:** an earlier read-only inspection snapshot in this audit returned only OCI labels for the API; two subsequent repeated reads for the same reported container ID returned project/service Compose labels. These immutable-label snapshots conflict. The Compose inventory says two running services while Docker inventory shows three project containers; Compose config parsing without the environment file also stops because `APP_RUNTIME_PASSWORD` is required. The environment file was not read, so API config-file/working-directory/env-file linkage and the source of the conflicting label evidence remain unresolved. No invocation is asserted.

## C. Backup restore readiness

**Status: STRUCTURAL VALIDATION PASS; restore rehearsal not evidenced.**

- Latest archive: `/opt/apps/ai-teacher/backups/20261003T000444Z/education.dump`, root-owned mode `0600`, 197132 bytes.
- Manifest: `/opt/apps/ai-teacher/backups/20261003T000444Z/education.manifest.json`; its declared SHA-256 equals the archive hash: `8b914b72a778d65146817fd8b4b6e3a686202df8377013e1042c8991a4efe2ab`.
- Read-only `pg_restore --list` completed with exit code `0`. No restore, temporary database, or database write was performed.
- CI run 35588891399 also completed the disposable PostgreSQL migration and staging-smoke jobs successfully. The workflow at the qualified commit contains a disposable backup archive listing check.
- No production restore rehearsal evidence was found in this audit. Archive listing is not proof that restoration succeeds.
- The AI Teacher backup timer is loaded and active/enabled; its last trigger was 2026-10-03 03:34:44 server time. This is evidence of backup scheduling, not restore qualification.

## D. Rollback image and external compatibility boundary

**Status: BLOCKED / UNKNOWN.**

- The server's GHCR cache contains the current digest above. It does not establish a second, known-good rollback digest.
- Local legacy images exist, including `ai-teacher-staging-api:latest` (no OCI revision/source labels) and several `ai-teacher-pilot-api` gate-tagged images. Their compatibility with the current database state and external clients was not evidenced.
- A local archive named `/opt/apps/ai-teacher/artifacts/staging-api-canonical-0021-image.tar` exists (118224384 bytes; `ai-teacher:ai-teacher`, mode `0640`). It was not loaded or otherwise altered/inspected as an image, so it is not qualified as a rollback candidate.
- Read-only GHCR package version enumeration was denied with HTTP 403 because the available GitHub token lacks `read:packages`. No package permissions were changed, and no image was pulled.
- Prior Gate737A inspection found no active in-repository caller for the retired `POST /api/v1/teacher/v2/classrooms/{classroom_id}/members` route (HTTP 410); callers outside this repository remain unknown. This does not establish the full external compatibility boundary.

### Bounded access-log observation

- Read-only scan of existing `/var/log/nginx/*access.log*` files found **0 matching requests** for `POST /api/v1/teacher/v2/classrooms/{classroom_id}/members` in the scanned files.
- The scan emitted only aggregate method/path/status counts; it did not emit source IPs, query strings, user agents, or raw request lines. Zero observations in retained local logs do not establish that no external consumer exists, especially where log retention/rotation is incomplete.

## E. Migration risk and external compatibility

**Status: MIGRATION BLOCKED pending a separately authorized execution plan and qualification.** The observed production revision is `20260921_0022`; the candidate chain ends at `20261003_0026`. This section is source review only; no migration was run.

| Revision | Structural/data effects | Rollback and operational risk |
|---|---|---|
| `20260924_0023` (`0022` → `0023`) | Takes `ACCESS EXCLUSIVE` locks on `student_submissions` and `submission_reviews`; creates revision history, adds columns and indexes/FKs, backfills submission snapshots, updates current-revision/review links, replaces review constraints, and installs an immutability trigger. | Downgrade intentionally raises an error because history cannot be collapsed. Highest identified lock, data-transform, and rollback risk; requires production-sized timing/lock planning and a recovery strategy before any execution gate. |
| `20261003_0024` (`0023` → `0024`) | Adds `user_tenant_memberships`, indexes, and `resolve_tenant`; restricts PUBLIC execution and conditionally grants the resolver to `app_runtime`. | Downgrade drops function/indexes/table and therefore is not a safe rollback after membership data is written. |
| `20261003_0025` (`0024` → `0025`) | Adds SECURITY DEFINER bootstrap/provision/revoke/read functions. These functions write idempotency, tenant membership, and audit rows when called at runtime; migration definition revokes PUBLIC and conditionally grants only function execution to `app_runtime`. | Downgrade drops the functions; runtime feature compatibility depends on their presence. No schema/data backfill was identified in this migration itself. |
| `20261003_0026` (`0025` → `0026`) | Adds SECURITY DEFINER enroll/remove functions; runtime calls can write class-membership and audit rows. Migration revokes broad function access and conditionally grants execution to `app_runtime`. | Downgrade drops the functions; runtime feature compatibility depends on their presence. No schema/data backfill was identified in this migration itself. |

The source definitions do not prove live-database lock duration, table size, privileges, function compatibility, or recovery time. In particular, 0023’s non-collapsible revision history makes a simple downgrade unavailable; any remediation after partial/complete application needs an explicit recovery design, not an assumed reverse migration.
## Risks

1. A matching image digest and commit establish build linkage, but do not explain how the API container was created or whether its runtime configuration was reconciled with the listed Compose project.
2. No verified fallback image tied to an allowed rollback point and known database revision is available in the evidence collected.
3. External API consumers are not inventoried; the bounded log scan had zero hits, but compatibility impact cannot be bounded from repository callers or retained logs alone.
4. Backup listing verifies archive readability but does not establish restore success or recovery time.
5. Candidate migrations include a long-lock/backfill step with an intentionally unavailable downgrade and later destructive schema downgrades; the execution/rollback risk is not qualified for production.

## Recommended resolution

Obtain read-only GHCR/package evidence or an independently retained signed digest manifest to qualify a rollback candidate; separately document the approved deployment invocation that created the API container; establish external API consumer ownership/compatibility evidence; and schedule a restore rehearsal only under a separately authorized Gate and isolated non-production environment. Do not infer missing evidence or change the running server as part of this audit.

## Commander decision fields

- CI/BUILD: provenance artifact identifies the runtime digest; the artifact attestation reference is still a placeholder and registry package metadata could not be read with the available token.
- DEPLOY PROVENANCE: BLOCKED — Compose/API label snapshots conflict and deployment invocation remains unknown.
- BACKUP: checksum and pg_restore --list exit 0 verified; restore rehearsal not evidenced.
- ROLLBACK: BLOCKED — no previous independently qualified image is available.
- EXTERNAL COMPATIBILITY: repository caller absent; bounded retained-log query returned zero matches; outside consumers remain unknown.
- DATABASE: reported current 20260921_0022, target 20261003_0026; migration path carries high locking/backfill/non-downgrade risk at 0023.
- LEGACY RUNTIME PROVENANCE: BLOCKING — reason above.
- FINAL: RELEASE PREP NOT READY.

## Mutations

`NONE` — no Docker lifecycle operation, registry pull/build, database operation, env read/edit, secret exposure, or server configuration change was performed. The only new workspace artifact is this report; no commit was created.

## Final qualification

- `CI/BUILD`: identified image digest linked to CI artifact and OCI revision; attestation reference and full release/deploy invocation are not closed.
- `BACKUP`: checksum and archive listing validated; isolated restore rehearsal is not evidenced.
- `ROLLBACK`: no independently qualified previous image tied to an allowed rollback point.
- `EXTERNAL COMPATIBILITY`: no in-repository caller and zero matches in scanned retained logs; external dependency remains unknown.
- `DATABASE`: current revision reported as `20260921_0022`; candidate target `20261003_0026`; 0023 has ACCESS EXCLUSIVE locks, data backfill, and no downgrade; later steps add runtime-dependent functions and membership schema.
- `LEGACY RUNTIME PROVENANCE`: `BLOCKING` — compose/runtime attribution evidence conflicts and deployment invocation is unknown.
- `MUTATIONS`: `NONE`.
- `FINAL`: `RELEASE PREP NOT READY` (`PROVENANCE_BLOCKED`; restore/rollback and migration execution risk also remain unqualified).