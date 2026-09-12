from dataclasses import FrozenInstanceError
import pytest
from app.services.configuration import (
    PipelineConfiguration, resolve_configuration, validate_configuration,
)

def test_defaults_are_valid_and_safe() -> None:
    config = resolve_configuration()
    assert validate_configuration(config).valid
    assert not config.observability.include_payloads
    assert not config.observability.include_sensitive_fields

def test_resolution_is_deterministic_and_fingerprint_stable() -> None:
    context = {"version": "1.1.0", "workflow_limits": {"max_steps": 8}}
    left = resolve_configuration(context)
    right = resolve_configuration(context)
    assert left.canonical_json() == right.canonical_json()
    assert left.fingerprint == right.fingerprint

def test_invalid_and_unknown_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="sensitive_observability"):
        resolve_configuration({"observability": {"include_payloads": True}})
    with pytest.raises(ValueError, match="unknown configuration fields"):
        resolve_configuration({"secret": "nope"})

def test_immutable_nested_contract() -> None:
    config = PipelineConfiguration()
    with pytest.raises(FrozenInstanceError):
        config.version = "2.0.0"
    with pytest.raises(TypeError):
        config.lifecycle.allowed_transitions[0] = ("X", ())

def test_persian_zwnj_round_trip() -> None:
    config = resolve_configuration({"lifecycle": {"allowed_transitions": (("می‌شود\u200c", ("دانش‌آموز",)),)}})
    assert "می‌شود\u200c" in config.canonical_json()
    assert "دانش‌آموز" in config.canonical_json()

def test_incompatible_settings_are_rejected() -> None:
    with pytest.raises(ValueError, match="vector_sync_required"):
        resolve_configuration({"feature_flags": {"enable_vector_sync": False}})
