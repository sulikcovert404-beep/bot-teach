from app.services.knowledge_ingestion import (
    AssessmentUnit,
    OcrBlock,
    ReviewState,
    VectorAction,
    isolate_math,
    order_ocr_blocks,
    vector_action,
)


def test_persian_ocr_orders_right_to_left_columns() -> None:
    blocks = [OcrBlock("Q4", 1, column=0), OcrBlock("Q1", 1, column=1), OcrBlock("Q2", 1, column=1, top=1)]
    assert [b.text for b in order_ocr_blocks(blocks)] == ["Q1", "Q2", "Q4"]


def test_assessment_remains_atomic_and_normalized() -> None:
    unit = AssessmentUnit("سوال مي‌خواهم", ("گزینه ك",), "۱", "توضیح")
    value = unit.as_atomic_text()
    assert "سوال می‌خواهم" in value and "گزینه ک" in value and "پاسخ" in value


def test_math_isolated_without_reordering() -> None:
    assert isolate_math("شتاب $a=-9.8$ محاسبه") == (("text", "شتاب "), ("math", "$a=-9.8$"), ("text", " محاسبه"))


def test_vector_lifecycle_requires_approval_and_digest() -> None:
    assert vector_action(review_state=ReviewState.PENDING, indexed_digest=None, current_digest="a") is VectorAction.NOOP
    assert vector_action(review_state=ReviewState.APPROVED, indexed_digest=None, current_digest="a") is VectorAction.INDEX
    assert vector_action(review_state=ReviewState.APPROVED, indexed_digest="a", current_digest="b") is VectorAction.REBUILD
    assert vector_action(review_state=ReviewState.REJECTED, indexed_digest="a", current_digest="b") is VectorAction.REVOKE
