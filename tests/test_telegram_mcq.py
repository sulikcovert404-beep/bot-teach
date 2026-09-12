import pytest
from app.services.telegram_mcq import MCQState, parse_mcq_callback

def test_mcq_answer_flow():
    state=MCQState("2+2?",("3","4"),1,"چون جمع چهار می‌شود.")
    assert state.answer(1)==(True,"چون جمع چهار می‌شود.")
    assert state.answer(0)[0] is False

def test_malformed_callback_fails_closed():
    with pytest.raises(ValueError, match="MALFORMED_CALLBACK"): parse_mcq_callback("bad")
    assert parse_mcq_callback("mcq:lesson-1:0")==("lesson-1",0)
from app.services.telegram_mcq import callback_response

def test_callback_response_fail_closed():
    assert callback_response("bad") == "درخواست نامعتبر است."
    assert callback_response("mcq:l:1") == "پاسخ شما ثبت شد."
