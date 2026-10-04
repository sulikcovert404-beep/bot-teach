# Gate738V — Candidate Identity Reconciliation & Fresh Phase 0

Date: 2026-10-04  
Worktree: `D:\project\ai-teacher-gate731-target`  
Branch / base HEAD: `codex/gate731-target` / `e4140c4d55a2943c53ecc187a28729663073d48d`  
Candidate state: uncommitted; no reset, checkout, revert, cleanup, or commit performed.

## Verdict

`CANDIDATE_IDENTITY_RECONCILED / FRESH_PHASE0_PASS` — the frozen Gate738P manifest initially differed at one file, `app/api/routes/teacher.py`. Under the separately authorized Gate738W read-only image-evidence scope, the pre-Gate738T file was recovered from the exact historical image ID and verified against the frozen SHA-256. The normalized diff is limited to the Gate738T legacy 410 OpenAPI response-model/metadata change. The handler arguments and body are AST-identical; four line-ending-only changes occur in the same response-model edit region. Focused tests and the full local suite pass, and a deterministic replacement manifest was created and verified.

This closes candidate identity and local Phase 0 only. It does not qualify Environment A/B, execute a container, establish production/staging readiness, or authorize Gate738L/restore.

## Frozen candidate reconciliation

| Item | Result |
|---|---|
| Historical manifest | `docs/GATE738P_CANDIDATE_MANIFEST.json` |
| Historical manifest SHA-256 | `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1` |
| Historical entries | 407 |
| Exact current matches before recovery | 406 |
| Missing paths | 0 |
| Sole changed path | `app/api/routes/teacher.py` |
| Historical file SHA-256 | `7e377d01513ade7ddd226d0cfbdff8c6785ebddc37dbc39dd023668c87abeafb` |
| Current file SHA-256 | `78d79948c990a35efb827dc6b866b657d83b0c837f4faeb9528081bd1510e8c5` |
| Historical file size | 36,504 bytes |
| Current file size | 36,929 bytes |
| Registered worktrees checked | 42; no exact historical-hash copy |

The old source bytes were independently reconstructed into `temp/gate738w-image-evidence/teacher.py`; the worktree candidate file was not overwritten. Recovered SHA-256 and size exactly match the historical manifest entry.

### Gate738W image evidence

| Evidence | Result |
|---|---|
| Exact historical image ID used | `sha256:d3c95ece976ca6425b5fc5ee6b2b93cb73f0d1bea868e264de6fa0c0ef318fe2` |
| Export archive | `temp/gate738w-image-evidence/gate738p-image.tar` |
| Archive size | 121,912,320 bytes |
| Archive SHA-256 | `f11449de2742b7909c457a2a233a0cf22df91eaf96784b65e31e6d576d0c1e3b` |
| Image platform | `linux/amd64` |
| Rootfs layers | 13/13 uncompressed layer hashes match Engine `RootFS.Layers` diff IDs |
| Recovered file | `/app/app/api/routes/teacher.py` |
| Recovered file SHA-256 | `7e377d01513ade7ddd226d0cfbdff8c6785ebddc37dbc39dd023668c87abeafb` |
| Recovered file size | 36,504 bytes |

The Docker-save config digest (`4338ec952ce8bbd0c86b3afa97e2cdb9d093f42a7afb1db4f18433fde20ddcff`) differs from the Engine image ID. This discrepancy is explicitly retained as an evidence caveat. The exact requested Engine image ID was inspected/exported, and all 13 ordered layer diff IDs were independently verified against the Engine image metadata before reconstructing the target file. The exported manifest contained one image entry and no RepoTags because export was by image ID. No image was created, run, started, restarted, killed, copied from a container, removed, built, pulled, or pushed.

### Recovered delta assessment

After normalizing line endings, there are two localized textual changes:

1. Add `LegacyMembershipRetiredResponse(detail: str)` alongside the existing request model.
2. Change the legacy route’s documented response from 201 to 410, mark it deprecated, and attach the 410 response schema and retirement description.

The `add_persistent_member` handler arguments and AST statement-list body are identical between recovered and current files. The body remains the same HTTP 410 exception/detail; role/auth dependencies in the signature are unchanged. Four line-ending-only differences (CRLF to LF) occur on otherwise identical lines at/around the new model block. No unrelated normalized textual change was found. This matches the intent documented by Gate738T. Focused tests below additionally exercise authorization, no database-session resolution, runtime status behavior, and OpenAPI output.

## Gate738T and Phase 0 validation

Focused regression:

```text
python -m pytest -p no:cacheprovider -q \
  tests/test_legacy_tenant_membership_boundary.py \
  tests/test_gate738t_legacy_410_openapi_contract.py
3 passed
```

Full default test suite:

```text
python -m pytest -p no:cacheprovider -q
1007 passed, 23 skipped, 1 warning
exit code: 0
```

The skipped cases are environment-gated, including PostgreSQL qualification; this run is not a substitute for Environment A/B. The suite was checked for unintended Docker lifecycle execution; the destructive hard-crash qualification file is not collected by the default `test_*.py` naming pattern and has no imports/references from the default suite.

Static checks:

```text
python -m compileall -q app: PASS
Ruff on Gate738T contract test: PASS
git diff --check: PASS (Git emitted only configured LF/CRLF notices)
```

Critical invariant checks:

| Invariant | Result |
|---|---|
| Alembic heads | Exactly one: `20261004_0033` |
| Historical `20260919_0022` migration | Hash unchanged from historical manifest |
| Gate738P contract guard | Hash unchanged from historical manifest |
| Dockerfile / `.dockerignore` / `pyproject.toml` | Hashes unchanged from historical manifest |
| Migration-source reference to `20260921_0023` | None; one test comment mentions the text |
| Database access or mutation in this Gate | None |

The Docker Engine was available after the user reported starting Docker (`29.5.3`, Linux x86_64). `docker ps` was empty. This confirms daemon availability only and was not treated as environment qualification.

## Replacement deterministic manifest

Created: `docs/GATE738V_CANDIDATE_MANIFEST.json`  
Format: `codex-gate738v-candidate-manifest-v1`  
SHA-256: `e7720c946f0d84f683dadbf344346779e8de2da6e5b5e21de77858c0b9cab378`

The manifest records base HEAD `e4140c4d55a2943c53ecc187a28729663073d48d`, branch `codex/gate731-target`, and `UNCOMMITTED_CANDIDATE`. It records candidate image status `NOT_BUILT` and no candidate image ID. It contains the 407 historical candidate paths plus five verification inputs (412 total). Every listed path was rechecked for current size and SHA-256: `412/412 PASS`. The historical image ID is provenance evidence only, not a newly built candidate artifact.

## Scope and mutations

```text
Candidate source modification: NONE
Historical image inspect/export: YES, exact ID, read/export only (Gate738W)
Docker lifecycle/build/pull/push: NONE
DB/schema/migration: NONE
Production/Staging/SSH/DNS/Cloudflare: NONE
Backup transfer/restore: NONE
Commit/deploy/cleanup: NONE
New artifacts: Gate738V report and deterministic manifest; Gate738W evidence under temp/
Other pre-existing worktree changes: left untouched
```

## Remaining blockers and next decision

`Gate738V` identity reconciliation and local Phase 0 are complete. `Gate738L` and restore remain **HOLD** because the required Environment A and Environment B handoff/qualification inputs are still not provided. The fresh local test run does not qualify PostgreSQL-dependent or runtime/container behavior. The config-digest difference is documented and bounded by the verified exact Engine image reference plus matching 13-layer diff-ID chain; Commander may decide whether this evidence is sufficient for the next artifact gate.

**Recommended next task:** Commander review of this report, replacement manifest, and Gate738W evidence, then issue a separate Gate for Environment A/B qualification or specify an additional provenance check. No additional Docker action is implied.

**Final:** `CANDIDATE_IDENTITY_RECONCILED / FRESH_PHASE0_PASS`; `Gate738L/restore = HOLD`.
