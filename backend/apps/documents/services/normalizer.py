from __future__ import annotations

import re
import unicodedata

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HORIZONTAL_WHITESPACE = re.compile(r"[ \t]+")
EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(value: str) -> str:
    # PDF extractors may return malformed lone Unicode surrogates.
    # Replace them before PostgreSQL or MinIO serialization.
    value = value.encode("utf-8", errors="replace").decode("utf-8")
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = CONTROL_CHARACTERS.sub("", text)

    lines = [HORIZONTAL_WHITESPACE.sub(" ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = EXCESS_BLANK_LINES.sub("\n\n", text)
    return text.strip()


def word_count(value: str) -> int:
    return len(re.findall(r"\b\w+\b", value, flags=re.UNICODE))


def token_estimate(value: str) -> int:
    if not value:
        return 0
    return max(1, round(len(value) / 4))
