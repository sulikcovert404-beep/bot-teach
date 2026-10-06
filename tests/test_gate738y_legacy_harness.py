from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from scripts import gate738p_contract_upgrade
from tests.gate738y_contract_model import (
    CONTRACT_TARGETS,
    FINAL_TARGET,
    PRE_CONTRACT_TARGET,
    ContractEvidence,
    may_request_contract,
)


def test_current_migration_lineage_has_one_explicit_final_head() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20261006_0034"]
    assert script.get_revision("20261006_0034").down_revision == FINAL_TARGET
    migration_files = list((root / "migrations" / "versions").glob("*.py"))
    assert not any(
        "20260924_0023" in path.name or "20260924_0023" in path.read_text(encoding="utf-8")
        for path in migration_files
    )
    assert gate738p_contract_upgrade.CONTROL_TARGET == PRE_CONTRACT_TARGET
    assert tuple(gate738p_contract_upgrade.CONTRACT_TARGETS) == CONTRACT_TARGETS
    assert gate738p_contract_upgrade.CONTRACT_TARGETS["20261003_0030"] == PRE_CONTRACT_TARGET
    assert gate738p_contract_upgrade.CONTRACT_TARGETS["20261003_0031"] == "20261003_0030"
    assert gate738p_contract_upgrade.CONTRACT_TARGETS[FINAL_TARGET] == "20261003_0031"


def test_unready_candidate_never_requests_contract_migration(monkeypatch) -> None:
    monkeypatch.setenv("EXPECTED_MIGRATION_HEAD", "20261003_0030")
    monkeypatch.setenv("GATE738P_ACTION", "")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://disposable/test")
    monkeypatch.setenv("WRITER_GENERATION", "candidate-y")
    monkeypatch.setenv("WRITER_DATABASE_ROLE", "candidate_y")
    requested: list[str] = []

    def reject_candidate(_expected_head: str) -> None:
        raise RuntimeError("candidate is not ready")

    monkeypatch.setattr(gate738p_contract_upgrade, "_candidate_ready", reject_candidate)
    monkeypatch.setattr(gate738p_contract_upgrade, "_run_alembic", requested.append)
    with pytest.raises(RuntimeError, match="candidate is not ready"):
        gate738p_contract_upgrade.main()
    assert requested == []


def test_candidate_not_eligible_blocks_contract_request() -> None:
    assert not may_request_contract(ContractEvidence(False, "FENCED", 0, True))


def test_old_generation_not_fenced_blocks_contract_request() -> None:
    assert not may_request_contract(ContractEvidence(True, "DRAINING", 0, True))


def test_unknown_active_writer_evidence_blocks_contract_request() -> None:
    assert not may_request_contract(ContractEvidence(True, "FENCED", None, True))


def test_unknown_database_quiescence_blocks_contract_request() -> None:
    assert not may_request_contract(ContractEvidence(True, "FENCED", 0, None))


def test_all_independent_guards_allow_requesting_contract_stage() -> None:
    assert may_request_contract(ContractEvidence(True, "FENCED", 0, True))
