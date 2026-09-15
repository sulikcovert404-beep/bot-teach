# Production Recovery Handoff Checklist — 2026-09-14

## Purpose and ownership

This checklist is the handoff contract for the next explicitly authorized recovery gate. It records prerequisites and the exact sequence without performing any lifecycle operation. The canonical target is the new production host; old production and `mentor-bot` remain outside scope.

## Current production snapshot

```text
Host: 95.135.208.167 (srv20708.deluxhost.net)
Database revision: 20260912_0021
Runtime image: sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd
Migration: complete
Production mutation in this handoff: NONE
```

## Preconditions

- [ ] SSH command execution completes within a bounded timeout.
- [ ] `sudo` capability is verified without printing or storing credentials.
- [ ] Docker socket responds consistently to read-only inspection.
- [ ] Host filesystem and I/O indicators are normal; no D-state recurrence.
- [ ] Canonical API container identity and image digest match the approved runtime.
- [ ] PostgreSQL and Redis are healthy.
- [ ] Database head remains `20260912_0021`.
- [ ] No active incident, storage stall, or unexpected container state is present.

## Exact recovery sequence (execute only after an explicit gate)

1. Re-verify host stability and bounded SSH command execution.
2. Verify Docker daemon and canonical container provenance.
3. Operate only on the approved API container, with the command explicitly authorized by the recovery gate.
4. Verify the running image digest and container state.
5. Check local `/health` and `/health/ready`.
6. Check public `/health` and `/health/ready`.
7. Confirm DB revision `20260912_0021`, PostgreSQL, and Redis health.
8. Run the approved smoke validation and record real output.
9. Stop immediately if any abort condition occurs.

## Abort conditions

Stop and report if any of the following occurs:

- Docker command timeout or socket hang;
- I/O degradation, D-state process, filesystem error, or storage stall;
- unexpected container/image identity or restart loop;
- readiness/schema mismatch or DB revision other than `20260912_0021`;
- health endpoint failure;
- evidence of cross-service or production mutation outside the authorized scope.

## Ownership boundary

This handoff does not authorize:

- database writes, migration, downgrade, schema, or RLS changes;
- environment or credential edits;
- Cloudflare or Telegram webhook changes;
- rebuild, pull, prune, volume changes, or host reboot;
- touching old production, the old tunnel, or `mentor-bot`;
- feature work, refactoring, or artifact rebuild.

## Evidence recording

For each executed step, record command intent, timestamp, exit status, and sanitized result. Never record secrets, tokens, private data, or complete environment values. A PASS requires direct evidence from the current host; prior reports are context only.

## Gate status

```text
Recovery handoff: READY FOR EXPLICIT GATE, NOT EXECUTED
Docker/Host stability: HOLD
API readiness: PENDING
Database: 20260912_0021 (reported evidence)
Production mutation: NONE
```
