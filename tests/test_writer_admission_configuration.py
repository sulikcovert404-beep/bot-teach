import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_writer_admission_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.writer_admission_enabled is False


def test_writer_admission_requires_nonsecret_release_and_instance_ids() -> None:
    with pytest.raises(ValidationError, match="WRITER_GENERATION"):
        Settings(writer_admission_enabled=True, writer_instance_id="api1", _env_file=None)
    with pytest.raises(ValidationError, match="WRITER_INSTANCE_ID"):
        Settings(writer_admission_enabled=True, writer_generation="release-123", _env_file=None)

    settings = Settings(
        writer_admission_enabled=True,
        writer_generation="release-123",
        writer_instance_id="api1",
        writer_database_role="candidate_role",
        _env_file=None,
    )
    assert settings.writer_generation == "release-123"
    assert settings.writer_instance_id == "api1"
    assert settings.writer_database_role == "candidate_role"


def test_writer_postgresql_application_name_maximum_identity_fits() -> None:
    settings = Settings(
        writer_admission_enabled=True,
        writer_generation="g" * 40,
        writer_instance_id="i" * 16,
        writer_database_role="candidate_role",
        _env_file=None,
    )
    assert len(f"aitw:{settings.writer_generation}:{settings.writer_instance_id}") == 62
