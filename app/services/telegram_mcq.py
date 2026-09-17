from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MCQState:
    question: str
    options: tuple[str, ...]
    answer_index: int
    explanation: str
    selected_index: int | None = None

    def answer(self, index: int) -> tuple[bool, str]:
        if index < 0 or index >= len(self.options):
            raise ValueError("MALFORMED_CALLBACK")
        correct = index == self.answer_index
        return correct, self.explanation


def parse_mcq_callback(data: str) -> tuple[str, int]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "mcq" or not parts[1]:
        raise ValueError("MALFORMED_CALLBACK")
    try: index = int(parts[2])
    except ValueError as exc: raise ValueError("MALFORMED_CALLBACK") from exc
    return parts[1], index
from app.services.telegram_mcq import parse_mcq_callback


def callback_response(callback_data: str | None) -> str:
    """Return a controlled Telegram callback response; never generate content."""
    if not callback_data:
        return "درخواست نامعتبر است."
    try:
        _lesson, _index = parse_mcq_callback(callback_data)
    except ValueError:
        return "درخواست نامعتبر است."
    return "پاسخ شما ثبت شد."
