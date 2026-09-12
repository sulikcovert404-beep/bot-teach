import pytest

from app.services.runtime_admission_bundle import (
    BundleOutcome,
    ReferenceStatus,
    ReferenceToken,
    RuntimeAdmissionBundle,
    build_runtime_admission_bundle,
    validate_runtime_admission_bundle,
)


def ref(name: str, status=ReferenceStatus.VALID) -> ReferenceToken:
    return ReferenceToken(name, "sha256:" + name.encode().hex().ljust(64, "0")[:64], status)


def make(**changes):
    values = dict(
        bundle_id="bundle-1", target_stage="PUBLISH",
        release_decision_reference=ref("release"), stage_admission_reference=ref("stage"),
        runtime_entry_reference=ref("entry"), environment_reference=ref("environment"),
        evidence_references=(ref("evidence"),), validation_references=(ref("validation"),),
        trace_reference=ref("trace"),
    )
    values.update(changes)
    return RuntimeAdmissionBundle(**values)


def test_valid_bundle_and_trace_linkage():
    bundle = make()
    assert validate_runtime_admission_bundle(bundle) is BundleOutcome.VALID
    assert bundle.trace_reference.reference_id == "trace"
    assert bundle.digest_matches()


def test_missing_required_reference_rejected():
    with pytest.raises(ValueError):
        make(evidence_references=())


def test_blocked_dependency_cannot_create_bundle():
    outcome, bundle = build_runtime_admission_bundle(
        bundle_id="b", target_stage="PUBLISH", release_decision_reference=ref("r"),
        stage_admission_reference=ref("s", ReferenceStatus.BLOCKED), runtime_entry_reference=ref("e"),
        environment_reference=ref("env"), evidence_references=(ref("ev"),),
        validation_references=(ref("v"),), trace_reference=ref("t"),
    )
    assert outcome is BundleOutcome.BLOCKED
    assert bundle is None


def test_invalid_and_review_dependencies_are_classified():
    assert validate_runtime_admission_bundle(make(runtime_entry_reference=ref("e", ReferenceStatus.INVALID))) is BundleOutcome.INVALID
    assert validate_runtime_admission_bundle(make(runtime_entry_reference=ref("e", ReferenceStatus.REQUIRES_REVIEW))) is BundleOutcome.REQUIRES_REVIEW


def test_digest_mismatch_is_invalid():
    bundle = make()
    object.__setattr__(bundle, "bundle_digest", "sha256:" + "0" * 64)
    assert validate_runtime_admission_bundle(bundle) is BundleOutcome.INVALID


def test_deterministic_serialization_and_immutability():
    first, second = make(), make()
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.bundle_digest == second.bundle_digest
    with pytest.raises((AttributeError, TypeError)):
        first.target_stage = "OTHER"


def test_persian_nfc_zwnj_round_trip():
    bundle = make(target_stage="مرحله پیش‌نویس")
    assert "پیش‌نویس".encode("utf-8") in bundle.canonical_bytes()
    assert bundle.digest_matches()


def test_secret_like_values_are_rejected():
    with pytest.raises(ValueError):
        ref("api_key=secret")
