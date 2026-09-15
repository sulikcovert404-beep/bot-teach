# Production Access Recovery Record — 2026-09-14

## Current SSH state

- Target: `95.135.208.167`
- Transport: PASS (TCP/22 reachable; SSH handshake completed)
- User `codex` authentication: FAILED/BLOCKED (key offered, no server acceptance)
- User `root` authentication: FAILED (`Permission denied (publickey,password)`)
- Remote command execution: UNAVAILABLE
- Mutation performed: NONE

## Recovery prerequisites

- [ ] Restore a valid SSH identity for an authorized user
- [ ] Verify `codex` sudo access (if required)
- [ ] Verify remote command execution
- [ ] Reopen Docker/API recovery gate by Commander

## Current hold

No compose operation, container recreation, environment recovery, Docker restart, database operation, or migration is permitted while SSH authentication remains blocked.

Production DB and migration state remain unchanged according to the latest Commander record (`20260912_0021`).
