import hashlib
import pytest
from app.services.validation_traceability import *

D = hashlib.sha256(b"x").hexdigest()
def ref(i): return TraceReference(i, "validation", D, "v1")
def test_reference_and_canonical_are_deterministic():
    c = ValidationTraceContext("t1", ref("r"), ref("d"), (ref("e"),), ref("p"), ref("s"))
    assert canonical_bytes(c.to_dict()) == canonical_bytes(c.to_dict())

def test_empty_graph_is_valid():
    validate_lineage([])

def test_missing_reference_rejected():
    with pytest.raises(TraceIntegrityError): validate_lineage([TraceEvent("a", "t", TraceEventType.CREATED, ref("a"), EdgeType.PARENT, "missing")])

def test_cycle_rejected():
    a=TraceEvent("a","t",TraceEventType.CREATED,ref("a"),EdgeType.PARENT,"b")
    b=TraceEvent("b","t",TraceEventType.EVALUATED,ref("b"),EdgeType.PARENT,"a")
    with pytest.raises(TraceIntegrityError): validate_lineage([a,b])

def test_correlation_is_separate_and_persian_safe():
    e=TraceEvent("a","ت",TraceEventType.CREATED,ref("می‌رود"),EdgeType.CORRELATION,correlation_id="c")
    validate_lineage([e])
