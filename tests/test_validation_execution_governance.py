from dataclasses import FrozenInstanceError

import pytest

from app.services.validation_execution_governance import *


def req(): return ValidationExecutionRequest("v1", "p1", "admin-ref", "ctx", ("read",), "evidence", "0" * 64)
def test_immutable():
    with pytest.raises(FrozenInstanceError): req().validation_id = "x"
def test_outcomes():
    r=req(); assert evaluate_request(r, approved_plan=True, evidence_available=True, authorized=True, granted_capabilities=("read",)).outcome is GovernanceOutcome.ALLOWED
    assert evaluate_request(r, approved_plan=True, evidence_available=True, authorized=False).outcome is GovernanceOutcome.DENIED
    assert evaluate_request(r, approved_plan=True, evidence_available=False, authorized=True).outcome is GovernanceOutcome.BLOCKED
def test_capability_and_digest():
    r=req(); assert evaluate_request(r, approved_plan=True, evidence_available=True, authorized=True).reason == "CAPABILITY_MISMATCH"
    assert evaluate_request(r, approved_plan=True, evidence_available=True, authorized=True, granted_capabilities=("read",), digest_valid=False).reason == "DIGEST_MISMATCH"
def test_determinism_and_persian():
    r=ValidationExecutionRequest("شناسه", "نسخه", "مرجع", "زمینه", ("خواندن\u200c",), "شواهد", "0"*64); assert r.canonical_bytes() == r.canonical_bytes(); assert b"\xd8" in r.canonical_bytes()
def test_secret_rejected():
    with pytest.raises(SecretLikeValueError): ValidationExecutionRequest("v", "p", "token: abcdefghijklmnop", "c", (), "e", "0"*64)
