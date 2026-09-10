# Adaptive Lesson Pack + Telegram MVP — Initial Execution Report

Status: PARTIAL

## Current evidence

- Existing persistence provides `Lesson`, `ContentGenerationJob`, `GeneratedAsset`, and `GenerationAttempt` models.
- `GenerationService` is provider-neutral and supports idempotent job reuse plus mock/gateway generation.
- Docker staging services are running and the API container is healthy.
- Focused generation regression passes (`tests/test_content_generation.py`: 1 passed).

## Gaps before implementation

- No canonical LessonPack orchestration service currently exists.
- Existing generation output is generic JSON and does not yet enforce the required podcast, PDF, MCQ, descriptive-question, answer, and age-profile schemas.
- Telegram route exists, but a verified staging flow from lesson selection through asset delivery is not yet established.
- Gemini TTS and external Telegram E2E remain credential/external-runtime dependent.

## Constraints

- No production changes.
- No live RLS or staging role mutation.
- Static assets must be generated once and reused; all provider calls remain behind application services.

## Next implementation slice

Define immutable provider-neutral lesson-pack contracts and a service orchestration layer on existing models, then add focused tests for profile differentiation, idempotent reuse, malformed output, and delivery eligibility before wiring Telegram staging UX.

## Follow-up

- Added build_or_reuse cache keyed by lesson, content version, stage, and language; repeated requests return the same immutable pack instance.
- Focused tests: lesson pack and orchestration suite => 8 passed.

## Qualification update

- Persisted asset reuse: PASS on disposable `InMemoryAssetStore`; retries and concurrent identical requests share one immutable pack.
- Version isolation: PASS; content versions use distinct persistence keys and hashes.
- Approval gating: PASS; unapproved packs are denied before delivery.
- Static delivery contract: PASS for podcast script, PDF markdown, MCQ, and descriptive assets.
- Real SQL `GeneratedAsset` adapter: BLOCKED / schema mapping required. Current models have no direct lesson/stage columns; no migration or staging writes were made.
- Real Telegram and Gemini TTS delivery: BLOCKED_EXTERNAL / BLOCKED_CREDENTIAL until external runtime and credentials are available.

