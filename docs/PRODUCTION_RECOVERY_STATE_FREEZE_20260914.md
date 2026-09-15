# Production Recovery State Freeze — 2026-09-14

## Current state

- Migration: `20260912_0021` complete
- Database: unchanged
- API runtime: pending restoration
- SSH transport: reachable
- SSH authentication: blocked for `codex` and `root`
- Remote command execution: unavailable
- Docker lifecycle action: prohibited while access is blocked

## Blocked actions

- API recreation or start
- Environment recovery or creation
- Docker restart/compose operations
- Database actions
- Migration actions

## Resume criteria

- SSH authentication succeeds for an authorized user
- `sudo -v` succeeds where required
- A remote command executes successfully

## Safety

No production mutation, secret disclosure, migration, database change, Docker operation, or environment edit was performed.
