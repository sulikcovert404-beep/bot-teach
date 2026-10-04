# Gate738U — Release Qualification Environment Handoff

**GATE:** Gate738U — Release Qualification Environment Handoff Package  
**VERDICT:** `PASS` — the handoff specification is complete. Runtime qualification remains `NOT READY` because the frozen candidate has a changed input and no eligible host is designated.  
**MODE:** Documentation and read-only verification only  
**PRODUCTION / STAGING:** `NO-GO`

## Current release state and frozen candidate

- Gate738P: `PASS` (candidate accepted/frozen; qualification incomplete)
- Gate738R: `PASS / PROVENANCE_VERIFIED`; migration `20260921_0022` canonical source verified
- Gate738T: `PASS`; legacy 410 OpenAPI contract aligned
- Gate738L: `CRASH_QUALIFICATION_ENV_BLOCKED / NOT QUALIFIED`
- Real backup restore: `NOT VERIFIED`
- Host-level IPv6 ingress: `NOT QUALIFIED`
- External legacy-410 client dependency: `UNKNOWN`; no active first-party caller found, absence of external clients is not proven

Frozen Gate738P identity recorded in the workspace manifest:

- Manifest: `docs/GATE738P_CANDIDATE_MANIFEST.json`
- Manifest SHA-256: `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1`
- Source HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Image ID: `sha256:d3c95ece976ca6425b5fc5ee6b2b93cb73f0d1bea868e264de6fa0c0ef318fe2`
- Platform: `linux/amd64`
- Alembic workspace head: single head `20261004_0033` (metadata inspection only; no database queried)
- Input inventory: 407 manifest entries; one current mismatch, detailed below
## Finding

The two required environment boundaries and their qualification requirements are specified below. No qualification host has been provisioned or designated by this Gate, and no backup restore environment is approved by this Gate.

The previously frozen Gate738P manifest file is present and its envelope SHA-256 matches the recorded frozen value `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1`. However, a fresh read-only check of all 407 manifest entries found one mismatch: `app/api/routes/teacher.py`. The manifest records SHA-256 `7e377d01513ade7ddd226d0cfbdff8c6785ebddc37dbc39dd023668c87abeafb`; the current workspace file hashes to `78d79948c990a35efb827dc6b866b657d83b0c837f4faeb9528081bd1510e8c5`. Git reports this file modified. This audit does not determine when or why it changed and does not inspect or reproduce its content.

Accordingly, Gate738L's frozen-candidate reopen condition is not satisfied. The candidate must not be resumed from this workspace. A new candidate manifest and a fresh Phase 0 are required under a separate authorization. No repair, rebuild, or manifest regeneration was performed here.

## Runtime qualification environment — requirements

This must be a disposable Linux x86_64 VM or host that is explicitly authorized for isolated test workloads. The local development machine's Docker Desktop Engine (`29.5.3`, `linux/x86_64`) responds to read-only `docker info`, but that does not establish an authorized Linux qualification host or permission to perform Docker lifecycle operations. Gate738L's prior attempt to create its disposable topology was blocked by command execution policy; no alternate route is authorized by Gate738U.

The designated host must provide Docker Engine and an explicitly approved execution path for creating, inspecting, stopping (including SIGKILL where authorized), restarting, and removing only Gate-owned containers, networks, and volumes. It must support a disposable PostgreSQL 16 instance and disposable Redis instance, two API services (OLD and CANDIDATE), and a controlled ingress. The database, Redis, and API backends must have no host-published ports. Only the Gate-owned ingress may publish a port, bound to an explicitly controlled interface. The host must provide both IPv4 and IPv6 ingress capability needed to qualify host-level Docker IPv6; the earlier Docker Desktop loopback environment did not qualify IPv6 ingress.

Use synthetic data and test-only values. Do not mount or connect to shared project resources, production/staging databases, real credentials, or protected containers. Allocate a unique Gate-specific project/resource namespace after host designation; record exact container, network, volume, and ingress identifiers before creating anything. The previously observed Gate738L prefixes and resources are historical evidence only and must not be reused or treated as authorization. No host, resource IDs, ingress address, or port has been designated by this Gate.

Required qualification sequence after a separately authorized environment is available:

1. Revalidate the newly authorized immutable candidate manifest and every listed input before any build or runtime operation.
2. Complete the exact Gate738L Phase 0 checks against the frozen OLD/CANDIDATE artifacts and isolated topology.
3. Run the staged migration only within the disposable PostgreSQL instance and only under its separately issued Gate's exact revision boundary; verify the expected migration head `20261004_0033` for the current candidate lineage.
4. Capture the contract-guard matrix, migration/rollback evidence, actual in-flight OLD API SIGKILL and restart behavior, fence persistence, false-quiescence behavior, and two independent clean qualification runs.
5. Capture the SMALL, MEDIUM, and STRESS lock matrix and IPv4 plus IPv6 ingress results. Synthetic health checks must show `/health` and `/health/ready`; API backends remain unpublished.
6. Retain logs, hashes, run identifiers, and exact resource inventory needed for review before any cleanup. Cleanup, if later authorized, may target only exact resources created by that run and recorded in its inventory. Never use broad prune, wildcards, or cleanup commands that can select shared/other-project resources.

The repository's read-only `python -m alembic heads` currently reports the single head `20261004_0033`. This confirms workspace migration metadata only; it says nothing about any database's applied revision.

## Gate738L reopen procedure

Gate738U does not reopen Gate738L. Before a future authorized qualification run:

- Establish the approved disposable Linux host and its exact isolation boundary.
- Obtain a newly accepted candidate freeze if any frozen input has changed. The current audit detected a changed manifest input, so the old freeze cannot be used to resume.
- Recompute the manifest envelope and every listed input hash, record the image identity/platform and provenance, and verify that the database lineage/expected revision matches the approved candidate.
- Start again at Gate738L Phase 0 only after the new freeze and execution path are accepted. If any frozen byte changes after that check, stop; do not repair or continue against the altered candidate.

Historical Gate738L reports remain evidence of their respective runs, not proof that the current workspace still matches the frozen candidate. The latest recorded Gate738L disposition is `CRASH_QUALIFICATION_ENV_BLOCKED` / `NOT QUALIFIED`; the present hash mismatch is a newly observed workspace-integrity blocker.

## Separate backup restore rehearsal environment — requirements

The backup rehearsal must use a distinct, approved, off-production disposable environment with controlled storage and restricted named access. Its owner must explicitly approve the data classification it may receive, specify the storage boundary, access controls, retention period, and verified destruction procedure, and document that network exposure is disabled or tightly controlled. Keep rehearsal data and resources separate from the runtime-qualification environment and from production/staging.

Gate738U does **not** authorize transfer, opening, or restoration of any real Production backup. No real backup path, checksum, credential, or contents are needed in this handoff. The earlier Gate738A evidence records that no environment had been approved for production-dump handling and no dump was copied, opened, or restored. A future real-backup rehearsal requires its own explicit Gate. Until then, an independently authorized synthetic-data rehearsal is the only alternative, and it must not be represented as proof of restoring a real Production backup.

## Cleanup and evidence boundary

No runtime or restore environment was created by this Gate, so there are no Gate738U containers, networks, volumes, databases, files, or backups to clean up. A future qualification run must record exact resources at creation and preserve its evidence before a separately authorized, exact-ID cleanup. No other project's files, containers, volumes, networks, compose projects, services, databases, ports, or processes may be changed.

Expected evidence from a future authorized runtime qualification includes the accepted candidate manifest and input-hash verification, image IDs/digests and labels, exact resource inventory, migration revision evidence, contract-guard matrix, SIGKILL/restart/fence results, false-quiescence checks, two-run records, lock matrix, IPv4/IPv6 health results, and exact cleanup inventory. Expected restore-rehearsal evidence is separate and must include approved data-handling controls, restore/listing/checksum results, migration/rollback findings, retention, and destruction evidence without exposing secret values.

## Status

- Runtime qualification requirements: `SPECIFIED`
- Runtime qualification host: `NOT DESIGNATED`
- Docker lifecycle authorization/path: `NOT ESTABLISHED`; prior Gate738L attempt was blocked by policy
- Current frozen candidate integrity: `MISMATCH — 1 OF 407 INPUTS`
- Current workspace Alembic head: `20261004_0033` (metadata inspection only)
- Approved real-backup restore environment: `NOT DESIGNATED`
- Real Production backup transfer: `NOT AUTHORIZED`
- Evidence confirms real Production backup restore: `NO`
- Production / staging: `NO-GO`

## Infrastructure handoff checklist

Runtime qualification:

- [ ] Disposable Linux x86_64 host/VM available and isolated from Production/Staging
- [ ] Docker lifecycle explicitly permitted: create/run, start, stop, restart, SIGKILL/kill, and remove
- [ ] Docker network create/remove permitted; private backend network supported
- [ ] Docker volume create/remove permitted
- [ ] PostgreSQL 16 disposable instance and Redis disposable instance permitted
- [ ] Synthetic-data-only OLD API, CANDIDATE API, and controlled ingress permitted
- [ ] Only ingress exposed to host; API, PostgreSQL, and Redis backend ports unpublished
- [ ] IPv4 host ingress supported
- [ ] Host-level IPv6 ingress through Docker ingress to candidate supported
- [ ] Candidate manifest and all 407 input hashes revalidated; current mismatch resolved only by a new approved freeze and Phase 0
- [ ] Evidence export and exact-ID cleanup path approved

Separate real-backup restore environment:

- [ ] Approved off-production isolated storage location and owner designated
- [ ] Named/restricted access and operator identities documented
- [ ] Retention duration documented
- [ ] Destruction method and verification documented
- [ ] Network exposure disabled; no application-user traffic
- [ ] Separate Gate authorizing any real Production backup transfer: NOT ISSUED
- [ ] Production backup transfer: NOT APPROVED
## Mutations

- Workspace mutation: this Gate738U report only
- Docker/container/network/volume operation: `NONE`
- Database read or write: `NONE`
- Backup transfer or restore: `NONE`
- Build, image pull, deployment, service restart, commit, or cleanup: `NONE`
- Production, staging, `mentor-bot`, `codesho_staging`, or other project touched: `NO`

## Final

The handoff package is ready for Infra review; neither runtime qualification nor restore execution is authorized or ready. The current Gate738P freeze cannot be resumed because one of its 407 manifest inputs differs. Preserve the mismatch as found; obtain a separately authorized new candidate freeze/Phase 0 and designate the disposable Linux host before runtime qualification. Real-backup restore remains separately blocked pending an approved environment and a distinct Gate.


