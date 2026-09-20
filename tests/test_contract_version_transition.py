from dataclasses import FrozenInstanceError
import unicodedata

import pytest

from app.services.contract_version_transition import *


def test_record_is_immutable_and_digest_bound():
    r = ContractVersionRecord("c", "rag", "1", "2", "chg", CompatibilityClass.COMPATIBLE, ("رابط",), "trace")
    assert r.verify_digest() and r.canonical_bytes() == r.canonical_bytes()
    with pytest.raises(FrozenInstanceError): r.current_version = "3"

def test_compatibility_and_decision():
    assert promotion_allowed(CompatibilityClass.COMPATIBLE)
    assert not promotion_allowed(CompatibilityClass.UNKNOWN)
    d = ContractTransitionDecision("1", "2", CompatibilityClass.REQUIRES_REVALIDATION, ("e1",), ("v1",))
    assert d.decision_digest == d.compute_digest()

def test_bad_digest_and_secrets():
    with pytest.raises(TransitionError): ContractVersionRecord("c", "rag", None, "1", "token=x", CompatibilityClass.UNKNOWN, (), "t")

def test_graph_cycle_and_broken_parent():
    with pytest.raises(TransitionError): VersionGraph({"1":"2", "2":"1"})
    with pytest.raises(TransitionError): VersionGraph({"2":"missing"})
    g = VersionGraph({"1":None, "2":"1", "3":"1"})
    assert g.ancestors("3") == ("3", "1") and g.successors("1") == ("2", "3")

def test_persian_unicode_safety():
    r = ContractVersionRecord("c", "آموزش", "۱", "۲", "تغییر", CompatibilityClass.UNKNOWN, (unicodedata.normalize("NFD", "می\u200cرود"),), "ردیابی")
    assert unicodedata.is_normalized("NFC", r.affected_components[0]) and "\u200c" in r.affected_components[0]
