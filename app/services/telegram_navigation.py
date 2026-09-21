"""Provider-neutral Telegram navigation contracts.

This module only builds validated navigation intents and Bot API markup.  It
does not send messages, handle callbacks, or change the active Telegram
route; those actions require a later controlled integration gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse, urlunparse


class NavigationAction(StrEnum):
    OPEN_CLASS = "open:class"
    OPEN_TUTOR = "open:tutor"
    OPEN_EXAM = "open:exam"
    OPEN_PROGRESS = "open:progress"
    HELP = "help"


@dataclass(frozen=True)
class NavigationIntent:
    action: NavigationAction
    label: str
    web_app: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("navigation label is required")


@dataclass(frozen=True)
class NavigationConfig:
    web_app_url: str
    schema_version: str = "telegram-nav-v1"

    def __post_init__(self) -> None:
        parsed = urlparse(self.web_app_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("web_app_url must be a fixed HTTPS URL without query or fragment")
        if not self.schema_version.strip():
            raise ValueError("schema_version is required")


def allowed_callback(value: str) -> NavigationAction | None:
    """Map only known callback identities; never interpret arbitrary input."""
    try:
        return NavigationAction(value)
    except ValueError:
        return None


def default_intents() -> tuple[NavigationIntent, ...]:
    return (
        NavigationIntent(NavigationAction.OPEN_CLASS, "ورود به کلاس هوشمند", web_app=True),
        NavigationIntent(NavigationAction.OPEN_TUTOR, "پرسش از مدرس هوشمند", web_app=True),
        NavigationIntent(NavigationAction.OPEN_EXAM, "آزمون", web_app=True),
        NavigationIntent(NavigationAction.OPEN_PROGRESS, "پیشرفت", web_app=True),
        NavigationIntent(NavigationAction.HELP, "راهنما"),
    )


def build_reply_keyboard(
    intents: tuple[NavigationIntent, ...] | None = None,
    *,
    web_app_url: str | None = None,
) -> dict[str, object]:
    """Build a deterministic provider-neutral reply keyboard payload."""
    chosen = intents or default_intents()
    rows: list[list[dict[str, object]]] = []
    for intent in chosen:
        button: dict[str, object] = {"text": intent.label}
        if intent.web_app and web_app_url:
            button["web_app"] = {"url": web_app_url}
        rows.append([button])
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def build_inline_keyboard(config: NavigationConfig, *, intents: tuple[NavigationIntent, ...] | None = None) -> dict[str, object]:
    """Build inline buttons; Web App actions use the fixed configured URL."""
    chosen = intents or default_intents()
    buttons: list[dict[str, object]] = []
    for intent in chosen:
        if intent.web_app:
            buttons.append({"text": intent.label, "web_app": {"url": config.web_app_url}})
        else:
            buttons.append({"text": intent.label, "callback_data": intent.action.value})
    return {"inline_keyboard": [buttons]}


def fallback_text(action: str) -> str:
    """Safe response for unknown or unavailable navigation actions."""
    return "برای ادامه از دکمه‌های منو استفاده کنید یا /help را بفرستید."


def role_menu_labels(role: str | None) -> tuple[str, ...]:
    """Return deterministic, presentation-only labels for a known role."""
    normalized = (role or "").strip().upper()
    if normalized == "TEACHER":
        return ("🏠 خانه", "🏫 کلاس‌های من", "📥 صف بررسی", "📚 محتوا", "📊 پیشرفت")
    if normalized == "SCHOOL_ADMIN":
        return ("🏠 خانه", "👥 کاربران", "🏫 کلاس‌ها", "📊 گزارش", "⚙️ تنظیمات")
    return ("🏠 خانه", "📚 درس‌های من", "📝 تمرین‌ها", "📊 پیشرفت من", "🤖 کمک هوشمند", "⚙️ تنظیمات")


def build_role_keyboard(role: str | None) -> dict[str, object]:
    """Build a presentation keyboard; authorization remains server-side."""
    return {
        "keyboard": [[{"text": label}] for label in role_menu_labels(role)],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def lesson_card_text(*, subject: str, grade: str | None = None, estimated_minutes: int | None = None) -> str:
    """Render a safe Persian lesson card without inventing unavailable data."""
    lines = ["📚 درس جدید آماده است", "", f"موضوع: {subject.strip()}"]
    if grade and grade.strip():
        lines.append(f"پایه: {grade.strip()}")
    if estimated_minutes is not None and estimated_minutes > 0:
        lines.append(f"زمان پیشنهادی: {estimated_minutes} دقیقه")
    lines.extend(["", "[شروع درس]  [بعداً]"])
    return "\n".join(lines)


def build_start_inline_keyboard(web_app_url: str, label: str = "🎓 ورود به پنل آموزشی") -> dict[str, object]:
    """Build a direct Inline WebApp button for /start message."""
    parsed = urlparse(web_app_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("web_app_url must be a fixed HTTPS URL")
    return {
        "inline_keyboard": [
            [{"text": label, "web_app": {"url": web_app_url}}]
        ]
    }


ROLE_DASHBOARD_PATHS: dict[str, str] = {
    "STUDENT": "/student-dashboard/",
    "TEACHER": "/teacher-dashboard/",
    "SCHOOL_ADMIN": "/admin-dashboard/",
    "SUPER_ADMIN": "/platform/",
}


def web_app_url_for_role(base_url: str, role: str | None) -> str:
    """Resolve the server-owned dashboard URL for a known backend role.

    Unknown or unresolved identities deliberately retain the configured Mini App
    fallback. Query strings and fragments are discarded from role routes.
    """
    parsed = urlparse(base_url)
    normalized = (role or "").strip().upper()
    path = ROLE_DASHBOARD_PATHS.get(normalized)
    if path is None:
        return base_url
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


__all__ = [
    "NavigationAction", "NavigationConfig", "NavigationIntent", "allowed_callback",
    "build_inline_keyboard", "build_reply_keyboard", "build_role_keyboard",
    "build_start_inline_keyboard", "default_intents", "fallback_text",
    "lesson_card_text", "role_menu_labels", "web_app_url_for_role",
]
