from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / ".github" / "scripts" / "gate_maos_a5i_readiness_diagnostics.py"
SPEC = importlib.util.spec_from_file_location("gate_maos_a5i_readiness_diagnostics", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
DIAGNOSTICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTICS)


def test_safe_head_accepts_only_revision_format() -> None:
    assert DIAGNOSTICS.safe_head("20261003_0029") == "20261003_0029"
    assert DIAGNOSTICS.safe_head("invalid revision with punctuation !") == "NOT_AVAILABLE"
    assert DIAGNOSTICS.safe_head({"unsafe": "value"}) == "NOT_AVAILABLE"
    assert DIAGNOSTICS.safe_head("") == "NOT_AVAILABLE"


def test_safe_revision_list_supports_multiple_heads_without_arbitrary_text() -> None:
    assert DIAGNOSTICS.safe_revision_list("20261003_0029") == "20261003_0029"
    assert DIAGNOSTICS.safe_revision_list("20261003_0029,20261004_0032") == (
        "20261003_0029,20261004_0032"
    )
    assert DIAGNOSTICS.safe_revision_list("database label with spaces") == "NOT_AVAILABLE"
    assert DIAGNOSTICS.safe_revision_list("") == "NO_ROWS"
    assert DIAGNOSTICS.safe_revision_list(["20261003_0029"]) == "NOT_AVAILABLE"


def test_readiness_fields_allowlist_reason_codes_and_revision() -> None:
    reason, head = DIAGNOSTICS.readiness_fields(
        503, b'{"detail":"Migration drift / Not ready","migration_head":"20261003_0029"}'
    )
    assert (reason, head) == ("MIGRATION_HEAD_MISMATCH", "20261003_0029")

    reason, head = DIAGNOSTICS.readiness_fields(
        503, b'{"detail":"unrecognized diagnostic text !@#","extra_field":"arbitrary"}'
    )
    assert (reason, head) == ("UNKNOWN", "NOT_AVAILABLE")
    assert DIAGNOSTICS.readiness_fields(503, b'{"detail":[]}') == (
        "UNKNOWN",
        "NOT_AVAILABLE",
    )
    assert DIAGNOSTICS.readiness_fields(200, b'{"status":"ready","migration_head":"20261003_0029"}') == (
        "READY",
        "20261003_0029",
    )


def test_db_identity_is_emitted_only_for_simple_allowlisted_identifiers() -> None:
    assert DIAGNOSTICS.safe_db_identity("ai_teacher|public|app_runtime|app_runtime") == (
        "ai_teacher|public|app_runtime|app_runtime"
    )
    assert DIAGNOSTICS.safe_db_identity("db|public|user label with spaces|postgres") == "NOT_AVAILABLE"
    assert DIAGNOSTICS.safe_db_identity("malformed") == "NOT_AVAILABLE"


def test_container_probe_programs_are_valid_python(monkeypatch) -> None:
    programs: list[str] = []

    def collect_probe(args: list[str], timeout: int = 12) -> str:
        programs.append(args[-1])
        return ""

    monkeypatch.setattr(DIAGNOSTICS, "_run", collect_probe)
    DIAGNOSTICS._effective_expected_head()
    DIAGNOSTICS._api_database_diagnostics()
    DIAGNOSTICS._redis_ping()

    assert len(programs) == 3
    for program in programs:
        compile(program, "<a5i-container-probe>", "exec")
