# Infrastructure I/O Incident Evidence Pack — 2026-09-14

## Incident

- ID: `HOST-IO-002`
- Severity: HIGH
- Impact: Blocks API recovery operations
- Host: `srv20708.deluxhost.net` (`95.135.208.167`)

## Read-only evidence

- SSH reachable.
- Load average observed: `4.81 2.27 1.07`.
- I/O PSI: `some avg10=99.80%`, `avg60=91.24%`, `avg300=40.01%`.
- I/O PSI full: `avg10=87.25%`, `avg60=81.12%`, `avg300=35.88%`.
- Root filesystem `/dev/vda1` ext4: 58G total, 15% used.
- PostgreSQL and Redis containers reported healthy.
- Canonical runtime config absent; `staging-api-1` absent.
- A bounded read-only command timed out during Docker/kernel evidence collection; D-state PID details remain incomplete due command quoting.

## Exclusions

No reboot, restart, process kill, container mutation, database mutation, migration, environment edit, rollback, or deployment was performed.

## Provider request

Please investigate storage latency, hypervisor/node health, I/O throttling, and kernel/filesystem storage stalls for `HOST-IO-002`.

## Current state

- Migration: complete (`20260912_0021`)
- Database: preserved
- API: not restored
- Runtime config: missing
- Infrastructure: I/O degraded
- Recovery: HOLD

This report contains no secrets, credentials, or private data.
