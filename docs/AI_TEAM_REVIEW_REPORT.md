# ADMIN PIPELINE VALIDATION TRACEABILITY CONTRACT FOUNDATION V1
## AI TEAM REVIEW REPORT

Status: Advisory review complete. No implementation changes applied.

## Agent responses

### Gemini — Traceability architecture
- Strengths: separates correlation from causation; provider-neutral trace model; cryptographic reference binding; deterministic canonical serialization.
- Risks: context loss across async boundaries, retry-induced causal cycles, payload growth, and bidirectional-text injection.
- Recommendations: immutable/frozen context and events, RFC 8785 canonical JSON, fail-safe observer dispatch, DAG conformance tests, W3C traceparent carrier, monotonic duration, immutable child derivation, and event-size limits.

### Qwen — Implementation and test strategy
- Strengths: clear parent/child/cause separation, fail-closed lineage validation, self-tracing of mismatch/repair/validation events, immutable snapshots, deterministic serialization, provider-neutral boundaries, and explicit Persian Unicode handling.
- Risks: conflated edge types, incomplete chains, cross-trace cycles, missing references, mutation during repair, untraced mismatches, mutable context, sequence gaps, replay identity errors, provider coupling, validation cost, and Persian text in structural fields.
- Recommendations: define the complete schema and edge taxonomy, distinguish validation modes and missing-reference classes, bind digests, specify self-tracing and replay/revalidation semantics, define sequence-gap behavior and projection contracts, set cost/persistence boundaries, add negative contracts, and build a Persian-focused test battery.

### GLM — Independent consistency and lineage
- Strengths: generalizes the completeness checker across the operational graph; digest-bearing references preserve lineage across retention; explicit derived-vs-event edge zones; content-provenance and operational-traceability join at retrieval hits; provider-neutral, registry-bound structural vocabulary.
- Risks: vacuous green results on an empty graph, correlation edges receiving integrity semantics, bare-ID references, conflated edge zones, a second validation surface beside the existing ledger, first-occurrence clock-skew alarms, operations-only scope, and orphan detection attempted only at write time.
- Recommendations: extend the existing ledger boundary and scheduled sweep; use `(target_id, target_digest, target_type)` references; validate parent/causation cardinality while treating correlation as well-formedness-only; distinguish legitimate retention purge from never-existed and tampered references; disclose zero nodes/edges; declare the content/operations join; use sequence authority with flag-before-alarm time-inversion handling; ship synthetic graph tests.

## Common points
1. Trace and correlation semantics must remain distinct; correlation is navigational and may be incomplete.
2. References must be immutable, digest-bound, and validated fail-closed.
3. Parent, causation, and correlation require separate edge types and rules.
4. Serialization must be deterministic and shared across providers and records.
5. Empty or synthetic datasets must disclose coverage to avoid vacuous confidence.
6. Persian handling requires UTF-8/NFC/ZWNJ/RTL tests, ASCII structural identifiers, and safe rendering of display text.
7. Validation should extend the existing provider-neutral persistence/ledger boundary instead of creating a parallel authority.

## Conflicts and distinctions
- Gemini emphasizes W3C propagation and event-size/async-context concerns; Qwen emphasizes schema completeness, replay semantics, and test boundaries; GLM emphasizes graph topology, retention-aware digest references, and extending the existing ledger.
- GLM proposes scheduled whole-graph orphan checks and a derived/event zone split. This complements, rather than contradicts, Gemini and Qwen.
- Correlation strictness differs in wording: all agents support well-formedness checks, while GLM explicitly rejects completeness/integrity enforcement for correlation edges.

## Codex validation
- The requested scope is contract review only; no database, event store, queue, worker, API, deployment, or audit-storage change was made.
- The three responses are consistent with the Commander’s constraints: provider-neutral design, immutable/digest-bound lineage, deterministic serialization, and Persian Unicode safety.
- The highest-risk false-confidence case is a green result over an empty graph; reports must show node/edge counts and distinguish contract conformance from exercised data.
- The most consequential schema decision is digest-bearing references with explicit retention/purge semantics. The most consequential architectural decision is extending the existing validation/ledger boundary rather than introducing a second checker authority.

## Recommendation
Adopt the common invariants as design requirements, then resolve the open schema decisions before implementation: edge-zone taxonomy, digest-bearing reference schema, correlation tolerance, empty-graph reporting, sweep ownership, and the retrieval-hit join. Add synthetic positive and negative tests covering cycles, missing/tampered/purged targets, replay, sequence gaps, serializer determinism, and Persian Unicode cases.

## Commander decision required
Please decide whether to approve these recommendations and the clarified traceability contract design. Codex will not implement changes until explicit Commander approval.
