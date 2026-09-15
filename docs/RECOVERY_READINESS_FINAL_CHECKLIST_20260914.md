# Recovery Readiness Final Checklist — 2026-09-14

## Locked State
- Database revision: `20260912_0021`
- Runtime image: `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`
- Migration: COMPLETE
- Recovery: HOLD
- Production mutation in this checklist: NONE

## Preconditions
- [ ] SSH command execution stable
- [ ] sudo verified without exposing secrets
- [ ] Docker socket responsive
- [ ] `docker info` completes without timeout
- [ ] Host I/O normalized; no D-state recurrence
- [ ] Canonical container provenance confirmed

## Authorized Recovery Sequence
1. Verify host stability.
2. Verify Docker daemon and socket.
3. Remove stale API container only if explicitly required by the recovery gate.
4. Recreate/start only canonical `staging-api-1` as authorized.
5. Verify image digest.
6. Check local/public `/health`.
7. Check local/public `/health/ready`.
8. Run bounded smoke validation.

## Validation Matrix
| Check | Expected |
|---|---|
| Image | `sha256:24c0135...` |
| DB | `20260912_0021` |
| Health | `200` |
| Ready | `200` |
| Migration | `0021` |
| PostgreSQL | Healthy |
| Redis | Healthy |

## Abort Rules
Abort and report on Docker timeout, renewed I/O degradation, D-state, DB mismatch, unexpected image/container, readiness regression, or any unapproved mutation request.

## Prohibited Before Gate
No Docker operation, restart, container lifecycle action, DB action, migration, environment edit, credential change, Cloudflare/webhook change, old-production change, or mentor-bot change.

## Decision
Recovery opens only after every precondition is evidenced and Commander issues an explicit operational gate. Until then: **Infrastructure HOLD; API recovery pending; production unchanged.**
