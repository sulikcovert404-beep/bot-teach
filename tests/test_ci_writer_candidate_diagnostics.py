"""Tests for bounded, secret-safe Gate738K CI diagnostics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import ci_bootstrap_writer_candidate as candidate_bootstrap


class FakeUndefinedTableError(Exception):
    sqlstate = "42P01"
    schema_name = "public"
    table_name = "missing_relation"
    column_name = None
    constraint_name = None


def test_assertion_diagnostic_is_deterministic_and_allowlisted() -> None:
    error = FakeUndefinedTableError(
        "password=do-not-log; SELECT * FROM secret_relation; postgresql://secret"
    )
    session = {
        "current_database": "ai_teacher_migrations",
        "current_schema": "public",
        "current_schemas": ["pg_catalog", "public"],
        "search_path": "\"$user\", public",
        "session_user": "ci_migrations",
        "current_user": "ci_migrations",
        "alembic_version_relation": "alembic_version",
        "writer_state_relation": "ai_teacher_writer_generation_state",
    }

    first = candidate_bootstrap._format_assertion_diagnostic(
        "writer_generation_rows", session, error
    )
    second = candidate_bootstrap._format_assertion_diagnostic(
        "writer_generation_rows", session, error
    )

    assert first == second
    assert first.startswith("GATE738K_ASSERTION_DIAGNOSTIC ")
    record = json.loads(first.removeprefix("GATE738K_ASSERTION_DIAGNOSTIC "))
    assert record["stage"] == "writer_generation_rows"
    assert record["error"] == {
        "exception_class": "FakeUndefinedTableError",
        "sqlstate": "42P01",
        "schema_name": "public",
        "table_name": "missing_relation",
        "column_name": None,
        "constraint_name": None,
    }
    assert "do-not-log" not in first
    assert "SELECT *" not in first
    assert "postgresql://" not in first


def test_assertion_diagnostic_marks_unavailable_fields_explicitly() -> None:
    class UnknownError(Exception):
        pass

    record = json.loads(candidate_bootstrap._format_assertion_diagnostic(
        "verified_database_connection", None, UnknownError("sensitive detail")
    ).removeprefix("GATE738K_ASSERTION_DIAGNOSTIC "))

    assert record["error"] == {
        "exception_class": "UnknownError",
        "sqlstate": None,
        "schema_name": None,
        "table_name": None,
        "column_name": None,
        "constraint_name": None,
    }
    assert all(value is None for value in record["session"].values())
    assert "sensitive detail" not in json.dumps(record)
