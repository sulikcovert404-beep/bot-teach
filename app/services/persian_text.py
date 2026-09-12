"""Deterministic Persian text safety helpers for ingestion and retrieval."""

from __future__ import annotations

import re
import unicodedata

_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه"})
_INVISIBLE = re.compile(r"[\u200b\u200d\u00ad\ufeff]")
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")


def normalize_persian_text(text: str) -> str:
    """Normalize glyphs and spacing without inventing or deleting words.

    ZWNJ is preserved, while zero-width space, joiner, BOM, and soft hyphen
    are removed. NFC makes index and query normalization identical.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    value = unicodedata.normalize("NFC", text).translate(_ARABIC_TO_PERSIAN)
    value = _INVISIBLE.sub("", value)
    value = _WHITESPACE.sub(" ", value)
    return "\n".join(line.strip() for line in value.splitlines()).strip()


def is_rtl_safe(text: str) -> bool:
    """Return false for control characters that can reorder visible content."""
    return not any(unicodedata.category(char) == "Cf" and char not in "\u200c" for char in text)
