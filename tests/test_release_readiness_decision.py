import unicodedata
from dataclasses import FrozenInstanceError

import pytest

from app.services.release_readiness_decision import *


def kwargs():
    return {"release_reference": "rel-1", "evaluated_contracts": ("c1",), "evidence_summary": ("e1",), "validation_summary": ("v1",), "transition_summary": ("t1",), "trace_reference": "trace-1"}

def test_ready_and_immutable():
    status, d = resolve_readiness(**kwargs()); assert status is ReadinessOutcome.READY and d.verify_digest()
    with pytest.raises(FrozenInstanceError): d.release_reference = "x"

def test_blocked_unknown_incompatible_and_digest():
    assert resolve_readiness(**kwargs(), blockers=("db",))[0] is ReadinessOutcome.BLOCKED
    assert resolve_readiness(**kwargs(), evidence_state="UNKNOWN")[0] is ReadinessOutcome.REQUIRES_REVIEW
    assert resolve_readiness(**kwargs(), transition_state=ContractState.INCOMPATIBLE)[0] is ReadinessOutcome.NOT_READY
    assert resolve_readiness(**kwargs(), digest_match=False)[0] is ReadinessOutcome.REQUIRES_REVIEW

def test_unicode_and_deterministic_serialization():
    k=kwargs(); k["evidence_summary"]=("پیش‌نویس",); d=ReleaseReadinessDecision(**k)
    assert unicodedata.is_normalized("NFC", d.canonical_bytes().decode()) and "\u200c" in d.canonical_bytes().decode()
    assert d.canonical_bytes()==ReleaseReadinessDecision(**k).canonical_bytes()

def test_secret_rejected():
    with pytest.raises(ValueError): ReleaseReadinessDecision(**{**kwargs(), "evidence_summary": ("api_key=bad",)})
