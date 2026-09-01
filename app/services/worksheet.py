from dataclasses import dataclass


def _persian_digits(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


@dataclass(frozen=True)
class WorksheetQuestion:
    prompt: str
    points: int = 1


def render_worksheet(title: str, instructions: str, questions: list[WorksheetQuestion]) -> str:
    if not title.strip() or not instructions.strip() or not questions:
        raise ValueError("Worksheet title, instructions, and questions are required")
    if any(not question.prompt.strip() or question.points < 1 for question in questions):
        raise ValueError("Worksheet questions are invalid")
    lines = [f"# {title.strip()}", "", instructions.strip(), ""]
    for index, question in enumerate(questions, start=1):
        lines.extend(
            [
                (
                    f"{_persian_digits(index)}. {question.prompt.strip()} "
                    f"({_persian_digits(question.points)} نمره)"
                ),
                "",
                "پاسخ: ",
                "",
            ]
        )
    return "\n".join(lines)
