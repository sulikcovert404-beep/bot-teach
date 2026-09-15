# Browser E2E Pre-Implementation Decision Closure Plan — 2026-09-15

## Purpose

Close the remaining execution decisions without creating dependencies, editing CI, installing browsers, or running E2E.

## 1. Node strategy

Record one supported Node LTS, its source of truth (runner image or repository tooling), and an update policy tied to security/support releases.

## 2. Package manager and lockfile

Select npm, pnpm, or yarn; assign a lockfile owner; require frozen-lockfile installs in CI; document how dependency updates are reviewed and scanned.

## 3. Runner

Select a pinned CI image, browser install strategy, and exact browser version. Record expected cache key inputs and invalidation conditions.

## 4. Trace retention

Set a short failure-only retention duration, name the artifact owner, and define deletion/access review. Redaction must happen before upload.

## 5. CI trigger

Choose pull-request-only, push-plus-pull-request, or an explicitly scheduled supplemental run. Keep browser E2E separate from the existing quality job and require unconditional teardown.

## Closure evidence

The decision record should be updated with selected values, owners, rationale, and Commander approval. Only then may an Implementation Gate authorize package/lockfile creation, workflow wiring, browser installation, and disposable E2E execution.

## Status

**DECISION CLOSURE PLAN READY / IMPLEMENTATION NOT AUTHORIZED.** No package, lockfile, workflow, browser, E2E, Production, runtime, secret, database, migration, Cloudflare, or Telegram change was made.
