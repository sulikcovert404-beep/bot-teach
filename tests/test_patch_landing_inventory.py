from app.services.patch_landing_inventory import *


def test_classification_and_completeness():
    assert classify(presence=True, conformance=True, dependency_closure=True) is InventoryClassification.READY
    assert classify(presence=True, conformance=False, dependency_closure=True) is InventoryClassification.PARTIAL
    assert classify(presence=False, conformance=False, dependency_closure=False) is InventoryClassification.MISSING
    assert classify(presence=True, conformance=True, dependency_closure=True, blocked=True) is InventoryClassification.BLOCKED
    assert classify(presence=None, conformance=True, dependency_closure=True) is InventoryClassification.UNKNOWN


def test_matrix_serialization_is_deterministic_and_hash_bound():
    e = InventoryEntry("configuration", "app/services/configuration.py", "V1", ("none",), ("VALID",), ("UTF8",), presence=True, conformance=True, dependency_closure=True, classification=InventoryClassification.READY).with_digest()
    d = DeltaRow("persistence", "contracts", "database tables", "architecture")
    g = EvidenceGate("migration", None)
    assert matrix_digest((e,), (d,), (g,)) == matrix_digest((e,), (d,), (g,))
    assert e.digest


def test_persian_round_trip_in_canonical_matrix():
    e = InventoryEntry("persian", "app/services/rag.py", "V1", state_vocabulary=("می‌شود", "تأیید‌شده"), serialization_rules=("NFC", "ZWNJ", "RTL"), classification=InventoryClassification.UNKNOWN)
    value = canonical_matrix((e,), (), ())
    encoded = __import__("json").dumps(value, ensure_ascii=False).encode("utf-8").decode("utf-8")
    assert "می‌شود" in encoded and "تأیید‌شده" in encoded and "ZWNJ" in encoded
