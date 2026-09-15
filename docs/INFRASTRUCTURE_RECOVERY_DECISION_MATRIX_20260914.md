# Infrastructure Recovery Decision Matrix — 2026-09-14

## Scope
Read-only decision support for production API recovery. No Docker, host restart, database, migration, environment, Cloudflare, webhook, or deployment operation is performed by this document.

## Current Blocker
| Signal | Status |
|---|---|
| Docker daemon | DEGRADED |
| Docker socket | Timeouts observed |
| Host I/O | High PSI previously observed |
| Container lifecycle | Unsafe until stability is requalified |
| API readiness | Pending |
| Database revision | `20260912_0021` |
| Production mutation | NONE |

## Recovery Options
| Option | Description | Risk | Gate |
|---|---|---|---|
| A | Wait for host stabilization, then requalify | Low | Preferred first step |
| B | Provider/storage investigation | Medium | Use if degradation persists |
| C | Host restart after explicit approval | Higher | Requires separate approval |
| D | Migration rollback | Not indicated | Do not pursue absent data/schema incident |

## Decision Criteria
Recovery may open only after evidence shows:
- Docker daemon responsive
- Docker socket stable under bounded commands
- Host I/O normalized with no D-state recurrence
- SSH command execution and sudo stable
- Canonical runtime/container provenance matches

## Recovery Sequence After Gate
1. Requalify host and storage read-only.
2. Verify Docker daemon and canonical container provenance.
3. Perform only the explicitly authorized API lifecycle action.
4. Verify local and public `/health` and `/health/ready`.
5. Verify DB/Redis health and migration revision.
6. Run bounded smoke validation and record evidence.

## Abort Conditions
Stop and report on Docker timeout, renewed I/O degradation, D-state, unexpected container/image state, DB revision mismatch, or any request for migration/env/schema change outside an explicit gate.

## Non-Goals
No DB rollback, migration reversal, schema change, app downgrade, host restart, or unrelated service cleanup is implied.

## Ownership and Decision
Infrastructure/Provider owner decides host remediation. Commander decides whether and when to open a recovery gate. Until then: **Incident OPEN / Recovery HOLD**.
