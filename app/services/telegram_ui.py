"""Provider-neutral Telegram UX component contracts.

Pure builders only: no network calls, webhook behavior, or authorization decisions.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.telegram_navigation import build_role_keyboard


@dataclass(frozen=True)
class UXMessage:
    kind: str
    text: str
    primary_action: str | None = None
    fallback_action: str | None = None


def main_menu(role: str | None) -> UXMessage:
    return UXMessage("main_menu", "منوی اصلی را انتخاب کنید.", fallback_action="/help")


def role_menu(role: str | None) -> UXMessage:
    return UXMessage("role_menu", "گزینه‌های در دسترس شما آماده است.", fallback_action="/menu")


def lesson_card(subject: str, *, grade: str | None = None, estimated_minutes: int | None = None) -> UXMessage:
    from app.services.telegram_navigation import lesson_card_text
    return UXMessage("lesson_card", lesson_card_text(subject=subject, grade=grade, estimated_minutes=estimated_minutes), "شروع درس", "بعداً")


def content_card(title: str) -> UXMessage:
    return UXMessage("content_card", f"📘 {title.strip()}", "باز کردن")


def progress_card(summary: str | None) -> UXMessage:
    text = summary.strip() if summary and summary.strip() else "پیشرفت شما هنوز داده قابل گزارش ندارد."
    return UXMessage("progress_card", text, fallback_action="/menu")


def error_message(message: str = "خطایی رخ داد.") -> UXMessage:
    return UXMessage("error", f"{message.strip()}\nلطفاً دوباره تلاش کنید.", "تلاش دوباره", "/help")


def empty_state(message: str = "هنوز محتوایی برای نمایش وجود ندارد.") -> UXMessage:
    return UXMessage("empty", message.strip(), fallback_action="/menu")


def confirmation_message(message: str) -> UXMessage:
    return UXMessage("confirmation", message.strip(), fallback_action="/menu")


class StudentKeyboard:
    @staticmethod
    def build() -> dict[str, object]:
        return build_role_keyboard("STUDENT")


class TeacherKeyboard:
    @staticmethod
    def build() -> dict[str, object]:
        return build_role_keyboard("TEACHER")


class SchoolAdminKeyboard:
    @staticmethod
    def build() -> dict[str, object]:
        return build_role_keyboard("SCHOOL_ADMIN")


class NavigationKeyboard:
    @staticmethod
    def build(role: str | None = None) -> dict[str, object]:
        return build_role_keyboard(role)


__all__ = ["NavigationKeyboard", "SchoolAdminKeyboard", "StudentKeyboard", "TeacherKeyboard", "UXMessage", "confirmation_message", "content_card", "empty_state", "error_message", "lesson_card", "main_menu", "progress_card", "role_menu"]
