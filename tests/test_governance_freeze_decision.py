import pytest

from app.services.governance_freeze_decision import (
    FreezeOutcome,
    GovernanceFreezeDecision,
    evaluate_freeze,
)
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken


def make(status=ReferenceStatus.VALID, trace=ReferenceStatus.VALID, reason="تصمیم معتبر"):
    r = lambda n: ReferenceToken(n, "sha256:" + n, status)
    return GovernanceFreezeDecision("f-1", r("baseline"), r("closure"), r("consistency"), r("handoff"), r("readiness"), reason, r("trace") if trace is ReferenceStatus.VALID else ReferenceToken("trace", "sha256:trace", trace))


def test_frozen_and_deterministic():
    d = make()
    assert evaluate_freeze(d) is FreezeOutcome.FROZEN
    assert d.freeze_digest == d.compute_digest()
    assert d.canonical_bytes() == make().canonical_bytes()


def test_warning_and_blocked_and_invalid():
    assert evaluate_freeze(make(trace=ReferenceStatus.REQUIRES_REVIEW)) is FreezeOutcome.FROZEN_WITH_EXCEPTIONS
    assert evaluate_freeze(make(status=ReferenceStatus.BLOCKED)) is FreezeOutcome.BLOCKED
    assert evaluate_freeze(make(status=ReferenceStatus.INVALID)) is FreezeOutcome.NOT_FROZEN


def test_unknown_and_digest_tamper_and_persian():
    assert evaluate_freeze(make(status=ReferenceStatus.REQUIRES_REVIEW)) is FreezeOutcome.UNKNOWN
    d = make(reason="ی‌ادداشت")
    object.__setattr__(d, "freeze_digest", "sha256:tampered")
    assert evaluate_freeze(d) is FreezeOutcome.NOT_FROZEN


def test_digest_and_secret_rejected():
    with pytest.raises(ValueError, match="digest"):
        GovernanceFreezeDecision("f", *([ReferenceToken("x", "sha256:x")] * 5), "ok", ReferenceToken("t", "sha256:t"), "sha256:bad")
    with pytest.raises(ValueError, match="secret"):
        make(reason="api_key leaked")
