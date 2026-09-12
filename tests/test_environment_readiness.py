from app.services.environment_readiness import CapabilityStatus, EnvironmentCapability, EnvironmentReadinessReport


def cap(name="database", status=CapabilityStatus.AVAILABLE, digest="sha256:proof"):
    return EnvironmentCapability(name, status, f"evidence:{name}", "probe-v1", "2026-09-03T00:00:00Z", digest)


def report(caps, blockers=(), summary="ok"):
    provisional = EnvironmentReadinessReport("staging", tuple(caps), tuple(blockers), "pending", summary)
    return EnvironmentReadinessReport("staging", tuple(caps), tuple(blockers), provisional.computed_digest, summary)


def test_available_environment_is_ready_and_digest_bound():
    item = report([cap()])
    assert item.is_ready and item.digest_matches()


def test_all_capabilities_are_supported():
    names = ("database", "migration", "vector", "runtime_service")
    item = report([cap(name) for name in names])
    assert {c.capability_name for c in item.capabilities} == set(names)


def test_unavailable_blocked_and_unknown_never_ready():
    for status in (CapabilityStatus.UNAVAILABLE, CapabilityStatus.BLOCKED, CapabilityStatus.UNKNOWN):
        item = report([cap(status=status)], blockers=("dependency blocked",))
        assert not item.is_ready


def test_available_requires_digest_and_secrets_are_rejected():
    import pytest
    with pytest.raises(ValueError):
        cap(digest="")
    with pytest.raises(ValueError):
        EnvironmentCapability("database", CapabilityStatus.UNKNOWN, "postgres://u:p@host", "probe-v1", "t", "")


def test_digest_is_deterministic_and_order_independent():
    first = report([cap("vector"), cap("database")])
    second = report([cap("database"), cap("vector")])
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.computed_digest == second.computed_digest


def test_digest_mismatch_is_detected():
    item = EnvironmentReadinessReport("staging", (cap(),), (), "sha256:wrong", "ok")
    assert not item.digest_matches() and not item.is_ready


def test_persian_nfc_zwnj_rtl_round_trip():
    summary = "وضعیت موتور جست‌وجو آماده است"
    item = report([cap()], summary=summary)
    encoded = item.canonical_bytes().decode("utf-8")
    assert "جست‌وجو" in encoded
    assert encoded == __import__("unicodedata").normalize("NFC", encoded)
