from datetime import UTC, datetime

from app.services.audit_trail import AuditHook, InMemoryAuditSink


def test_audit_event_serialization_preserves_persian_zwnj_and_rtl():
    sink=InMemoryAuditSink(); hook=AuditHook(sink, lambda: datetime(2026,1,1,tzinfo=UTC))
    e=hook.project(event_id="e1",command_id="c1",correlation_id="r1",causation_id="a1",actor={"id":"u"},action="accepted",target={"id":"x"},result_status="accepted",digest_reference="d",new_state={"title":"دانش\u200cآموز ‮RTL"})
    assert e.serialize() == e.serialize()
    assert "دانش\u200cآموز" in e.serialize()

def test_audit_rejection_and_validation_events():
    sink=InMemoryAuditSink(); hook=AuditHook(sink, lambda: datetime(2026,1,1,tzinfo=UTC))
    hook.project(event_id="e1",command_id="c1",correlation_id="r1",causation_id="a1",actor={},action="denied",target={},result_status="unauthorized")
    hook.project(event_id="e2",command_id="c2",correlation_id="r2",causation_id="a2",actor={},action="validation_failed",target={},result_status="validation_failed")
    assert [e.result_status for e in sink.events] == ["unauthorized", "validation_failed"]

def test_audit_requires_identifiers():
    try: AuditHook(InMemoryAuditSink()).project(event_id="",command_id="c",correlation_id="r",causation_id="a",actor={},action="x",target={},result_status="x")
    except ValueError: pass
    else: raise AssertionError("missing identifiers must fail")
