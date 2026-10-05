"""Static safety contract for split-writer Class A CI qualification."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IMAGE = (
    "pgvector/pgvector:0.8.7-pg16@sha256:"
    "7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a"
)
EXPECTED_DATABASE_URL = (
    "postgresql+asyncpg://ci_migrations:ci_only_ephemeral_migrations_password"
    "@127.0.0.1:5432/ai_teacher_migrations"
)


def _migration_contract_violations(workflow):
    violations = []
    job = workflow.get("jobs", {}).get("migration-contract", {})
    matrix = job.get("strategy", {}).get("matrix", {})
    if matrix.get("replay") != [1, 2]:
        violations.append("Class A must use two independent replay matrix jobs")
    postgres = job.get("services", {}).get("postgres", {})
    if postgres.get("image") != EXPECTED_IMAGE:
        violations.append("postgres image must retain the approved immutable pgvector/PG16 digest")
    if postgres.get("env") != {
        "POSTGRES_USER": "ci_migrations",
        "POSTGRES_PASSWORD": "ci_only_ephemeral_migrations_password",
        "POSTGRES_DB": "ai_teacher_migrations",
    }:
        violations.append("postgres service must use only its synthetic CI database identity")
    if "127.0.0.1:5432:5432" not in postgres.get("ports", []):
        violations.append("postgres service must bind only to loopback")

    steps = job.get("steps", [])
    names = [step.get("name", "") for step in steps]
    required = [
        "Check disposable PostgreSQL capabilities",
        "Verify disposable app_runtime role prerequisite",
        "Bootstrap disposable candidate writer role",
        "Verify explicit pre-control migration",
        "Verify writer control migration",
        "Assert Gate738K database contract",
    ]
    missing = [name for name in required if name not in names]
    if missing:
        return violations + [f"required isolated Class A step is missing: {name}" for name in missing]
    positions = [names.index(name) for name in required]
    if positions != sorted(positions):
        violations.append("PG capability, principal bootstrap, migration, and assertions are out of order")
    by_name = {step.get("name"): step for step in steps}

    for name in required[1:]:
        if by_name[name].get("env", {}).get("DATABASE_URL") != EXPECTED_DATABASE_URL:
            violations.append(f"{name} must target only its synthetic loopback PostgreSQL service")
    for name in (required[1], required[2], required[5]):
        if by_name[name].get("env", {}).get("CI_POSTGRES_SERVICE_ID") != "${{ job.services.postgres.id }}":
            violations.append(f"{name} must attest the exact PostgreSQL service container")
    if by_name[required[1]].get("run") != "python -B tests/ci_bootstrap_app_runtime.py":
        violations.append("app_runtime prerequisite must use the reviewed CI-only bootstrap helper")
    if by_name[required[2]].get("run") != "python -B tests/ci_bootstrap_writer_candidate.py":
        violations.append("candidate role must use the reviewed CI-only bootstrap helper")
    if by_name[required[5]].get("run") != (
        "python -B tests/ci_bootstrap_writer_candidate.py --assert-contract"
    ):
        violations.append("Class A contract assertions must use the read-only CI verifier")

    expand, control = by_name[required[3]], by_name[required[4]]
    if expand.get("env", {}).get("EXPECTED_MIGRATION_HEAD") != "20261003_0029":
        violations.append("Class A must explicitly target expand revision 20261003_0029")
    if control.get("env", {}).get("EXPECTED_MIGRATION_HEAD") != "20261004_0032":
        violations.append("Class A must stop at explicit control revision 20261004_0032")
    for step in (expand, control):
        run = step.get("run", "")
        if "python -B -m scripts.gate738p_contract_upgrade" not in run:
            violations.append("Class A migration must use the canonical fail-closed runner")
        if "alembic upgrade head" in run.lower() or "downgrade" in run.lower():
            violations.append("Class A must not use head or downgrade semantics")
    if control.get("env", {}).get("WRITER_GENERATION") != "${{ steps.candidate.outputs.writer_generation }}":
        violations.append("WRITER_GENERATION must be bound to the candidate created in this replay")
    if control.get("env", {}).get("WRITER_DATABASE_ROLE") != "${{ steps.candidate.outputs.writer_role }}":
        violations.append("WRITER_DATABASE_ROLE must be bound to the candidate created in this replay")
    if control.get("env", {}).get("WRITER_ADMISSION_ENABLED") != "true":
        violations.append("writer admission must be explicitly enabled for Class A contract migration")

    scoped = "\n".join(str(item) for item in [job.get("services", {}), *steps]).lower()
    if any(marker in scoped for marker in ("codesho", "production", "staging", "secrets.")):
        violations.append("Class A must not reference shared, Production, Staging, or secret DB bindings")
    if any(marker in scoped for marker in (
        "20261004_0033", "upgrade head", "alembic downgrade", "sigkill",
        "docker build", "candidate api startup", "old writer runtime",
    )):
        violations.append("hosted Class A must not claim Class B or revision 0033 qualification")
    return violations


def _load_workflow():
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def test_ci_qualifies_only_class_a_with_two_fresh_replays():
    workflow = _load_workflow()
    assert _migration_contract_violations(workflow) == []
    assert "migration-contract" in workflow["jobs"]["staging-smoke"]["needs"]
    assert "staging-smoke" in workflow["jobs"]["docker"]["needs"]


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        ("digest", "immutable pgvector/PG16 digest"),
        ("single_replay", "two independent replay matrix jobs"),
        ("non_loopback", "bind only to loopback"),
        ("candidate_missing", "step is missing"),
        ("candidate_target", "synthetic loopback PostgreSQL"),
        ("candidate_shared_reference", "shared, Production, Staging"),
        ("service_identity", "exact PostgreSQL service container"),
        ("candidate_static_role", "WRITER_DATABASE_ROLE must be bound"),
        ("generation_static", "WRITER_GENERATION must be bound"),
        ("wrong_expand", "20261003_0029"),
        ("wrong_control", "20261004_0032"),
        ("class_b_target", "0033 qualification"),
        ("downgrade", "head or downgrade"),
        ("skip_contract", "step is missing"),
    ],
)
def test_ci_migration_verifier_rejects_unsafe_contract_mutations(mutate, expected_fragment):
    workflow = deepcopy(_load_workflow())
    job = workflow["jobs"]["migration-contract"]
    steps = job["steps"]
    by_name = {step.get("name"): step for step in steps}
    if mutate == "digest":
        job["services"]["postgres"]["image"] = "postgres:16"
    elif mutate == "single_replay":
        job["strategy"]["matrix"]["replay"] = [1]
    elif mutate == "non_loopback":
        job["services"]["postgres"]["ports"] = ["5432:5432"]
    elif mutate == "candidate_missing":
        steps.remove(by_name["Bootstrap disposable candidate writer role"])
    elif mutate == "candidate_target":
        by_name["Bootstrap disposable candidate writer role"]["env"]["DATABASE_URL"] = EXPECTED_DATABASE_URL.replace("127.0.0.1", "shared-db")
    elif mutate == "candidate_shared_reference":
        by_name["Bootstrap disposable candidate writer role"]["run"] += " # staging"
    elif mutate == "service_identity":
        by_name["Assert Gate738K database contract"]["env"].pop("CI_POSTGRES_SERVICE_ID")
    elif mutate == "candidate_static_role":
        by_name["Verify writer control migration"]["env"]["WRITER_DATABASE_ROLE"] = "app_runtime"
    elif mutate == "generation_static":
        by_name["Verify writer control migration"]["env"]["WRITER_GENERATION"] = "candidate"
    elif mutate == "wrong_expand":
        by_name["Verify explicit pre-control migration"]["env"]["EXPECTED_MIGRATION_HEAD"] = "20261003_0031"
    elif mutate == "wrong_control":
        by_name["Verify writer control migration"]["env"]["EXPECTED_MIGRATION_HEAD"] = "20261004_0033"
    elif mutate == "class_b_target":
        by_name["Verify writer control migration"]["run"] += "\npython -m alembic upgrade 20261004_0033"
    elif mutate == "downgrade":
        by_name["Verify writer control migration"]["run"] += "\npython -m alembic downgrade base"
    elif mutate == "skip_contract":
        steps.remove(by_name["Assert Gate738K database contract"])

    violations = _migration_contract_violations(workflow)
    assert any(expected_fragment in violation for violation in violations), violations
