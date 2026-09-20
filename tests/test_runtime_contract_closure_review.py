from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_contract_closure_review import *


def ref(i,s=ReferenceStatus.VALID): return ReferenceToken(i,"sha256:"+i,status=s)
def base(**kw):
 d={"closure_id": "c","evaluated_contracts": [ref("a"),ref("b")],"dependency_graph": {"a":("b",),"b":()},"authority_map": {"admission":"a","execution":"b"},"version_summary": {"a":"1","b":"1"},"digest_summary": {"a":"sha256:a","b":"sha256:b"},"trace_reference": ref("trace")}; d.update(kw); return build_closure_review(**d)
def test_closed_and_deterministic():
 r=base(); assert validate_closure(r) is ClosureOutcome.CLOSED; assert r.digest_matches(); assert r.canonical_bytes()==base(evaluated_contracts=[ref("b"),ref("a")]).canonical_bytes()
def test_missing_cycle_authority():
 assert validate_closure(base(evaluated_contracts=[ref("a")])) is ClosureOutcome.OPEN
 assert validate_closure(base(dependency_graph={"a":("b",),"b":("a",)})) is ClosureOutcome.BLOCKED
 assert validate_closure(base(authority_map={"x":"a","y":"a"})) is ClosureOutcome.BLOCKED
def test_digest_trace_and_unicode():
 r=base(); object.__setattr__(r,"closure_digest","bad"); assert validate_closure(r) is ClosureOutcome.BLOCKED
 assert validate_closure(base(trace_reference=ref("trace",ReferenceStatus.BLOCKED))) is ClosureOutcome.BLOCKED
 assert "\u200c" in base(closure_id="پیش‌نویس").closure_id


def test_version_digest_trace_gap_and_self_reference():
 assert validate_closure(base(version_summary={"a":"1","b":"2"})) is ClosureOutcome.OPEN
 assert validate_closure(base(digest_summary={"a":"bad","b":"sha256:b"})) is ClosureOutcome.BLOCKED
 assert validate_closure(base(trace_reference=ref("trace",ReferenceStatus.REQUIRES_REVIEW))) is ClosureOutcome.UNKNOWN
 assert validate_closure(base(dependency_graph={"a":("a",),"b":()})) is ClosureOutcome.BLOCKED
