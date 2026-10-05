"""Unit checks for fail-closed source-bound writer qualification inputs."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import gate738p_contract_upgrade as migration_runner

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ci_bootstrap_writer_candidate as candidate_bootstrap


def test_candidate_names_are_source_and_replay_bound(monkeypatch):
    source_sha = "a" * 40
    monkeypatch.setenv("GITHUB_SHA", source_sha)
    monkeypatch.setenv("GATE738P_REPLAY_ID", "2")
    monkeypatch.setattr(
        candidate_bootstrap.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, source_sha + "\n", ""),
    )
    assert candidate_bootstrap._candidate_names() == ("gpc_aaaaaaaaaaaa_2", "ci_aaaaaaaaaaaa_2")


@pytest.mark.parametrize(
    ("source_sha", "replay"),
    [("candidate", "1"), ("a" * 40, "3"), ("A" * 40, "1"), ("a" * 39, "1")],
)
def test_candidate_names_reject_unbound_values(monkeypatch, source_sha, replay):
    monkeypatch.setenv("GITHUB_SHA", source_sha)
    monkeypatch.setenv("GATE738P_REPLAY_ID", replay)
    with pytest.raises(candidate_bootstrap.CandidateBootstrapError):
        candidate_bootstrap._candidate_names()


def test_candidate_names_reject_source_sha_not_matching_checkout(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GATE738P_REPLAY_ID", "1")
    monkeypatch.setattr(
        candidate_bootstrap.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "b" * 40 + "\n", ""),
    )
    with pytest.raises(candidate_bootstrap.CandidateBootstrapError, match="MISMATCH"):
        candidate_bootstrap._candidate_names()


@pytest.mark.parametrize(
    ("generation", "role"),
    [
        ("", "gpc_candidate"),
        ("bad/name", "gpc_candidate"),
        ("legacy", "gpc_candidate"),
        ("candidate", ""),
        ("candidate", "app_runtime"),
        ("candidate", "bad/name"),
    ],
)
def test_migration_runner_rejects_invalid_candidate_identity(monkeypatch, generation, role):
    monkeypatch.setenv("WRITER_GENERATION", generation)
    monkeypatch.setenv("WRITER_DATABASE_ROLE", role)
    with pytest.raises(RuntimeError, match="refused"):
        migration_runner._candidate_identity()


class _CandidateConnection:
    def __init__(self, role, memberships, can_assume=False):
        self.role = role
        self.memberships = memberships
        self.can_assume = can_assume

    async def fetchrow(self, _query, _role_name):
        return self.role

    async def fetch(self, _query, _role_name):
        return [{"rolname": name} for name in self.memberships]

    async def fetchval(self, _query, _role_name):
        return self.can_assume


@pytest.mark.parametrize(
    ("role", "memberships", "can_assume", "reason"),
    [
        (None, ["app_runtime"], False, "ATTRIBUTES_MISMATCH"),
        ({"rolcanlogin": False, "rolinherit": True, "rolsuper": False,
          "rolcreatedb": False, "rolcreaterole": False, "rolreplication": False,
          "rolbypassrls": False}, ["app_runtime"], False, "ATTRIBUTES_MISMATCH"),
        ({"rolcanlogin": True, "rolinherit": True, "rolsuper": False,
          "rolcreatedb": False, "rolcreaterole": False, "rolreplication": False,
          "rolbypassrls": False}, ["app_runtime", "extra_role"], False, "MEMBERSHIP_MISMATCH"),
        ({"rolcanlogin": True, "rolinherit": True, "rolsuper": False,
          "rolcreatedb": False, "rolcreaterole": False, "rolreplication": False,
          "rolbypassrls": False}, ["app_runtime"], True, "CAN_ASSUME_CANDIDATE"),
    ],
)
def test_candidate_role_contract_rejects_unsafe_identity(
    role, memberships, can_assume, reason
):
    connection = _CandidateConnection(role, memberships, can_assume)
    with pytest.raises(candidate_bootstrap.CandidateBootstrapError, match=reason):
        import asyncio

        asyncio.run(candidate_bootstrap._verify_candidate(connection, "gpc_candidate", "ci_candidate"))


def _evidence():
    return {
        "gate": "Gate738P",
        "candidate_generation": "candidate_123",
        "old_generation": "legacy",
        "old_container_exit_code": 137,
        "old_container_hard_killed": True,
        "inflight_transaction_rolled_back": True,
        "fence_persisted_after_restart": True,
        "restarted_old_write_denied": True,
        "candidate_health_remained_ready": True,
        "candidate_write_succeeded": True,
        "test_run_id": "run-123",
        "old_container_id": "container-123",
        "source_sha": "b" * 40,
        "candidate_image_digest": "sha256:" + "c" * 64,
    }


def _validate(tmp_path, monkeypatch, evidence, *, expected_sha=None, expected_digest=None):
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    monkeypatch.setenv("GATE738P_HARD_CRASH_EVIDENCE_FILE", str(evidence_path))
    migration_runner._require_hard_crash_evidence(
        "candidate_123",
        expected_sha if expected_sha is not None else "b" * 40,
        expected_digest if expected_digest is not None else "sha256:" + "c" * 64,
    )


def test_hard_crash_evidence_requires_exact_source_and_image_binding(tmp_path, monkeypatch):
    _validate(tmp_path, monkeypatch, _evidence())


@pytest.mark.parametrize(
    ("change", "expected_sha", "expected_digest"),
    [
        ("missing-source", "b" * 40, "sha256:" + "c" * 64),
        ("wrong-source", "b" * 40, "sha256:" + "c" * 64),
        ("wrong-image", "b" * 40, "sha256:" + "c" * 64),
        ("mutable-image", "b" * 40, "codex-gate738p-candidate-20261004"),
        ("missing-expected", "", "sha256:" + "c" * 64),
    ],
)
def test_hard_crash_evidence_fails_closed_on_provenance_mismatch(
    tmp_path, monkeypatch, change, expected_sha, expected_digest
):
    evidence = _evidence()
    if change == "missing-source":
        evidence.pop("source_sha")
    if change == "wrong-source":
        evidence["source_sha"] = "d" * 40
    if change == "wrong-image":
        evidence["candidate_image_digest"] = "sha256:" + "e" * 64
    with pytest.raises(RuntimeError, match="refused"):
        _validate(
            tmp_path, monkeypatch, evidence,
            expected_sha=expected_sha, expected_digest=expected_digest,
        )
