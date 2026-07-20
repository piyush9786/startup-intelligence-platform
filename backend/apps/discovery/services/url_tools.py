from __future__ import annotations

import posixpath
from urllib.parse import (
    parse_qsl,
    unquote,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from apps.sources.models import Source

from .adapters import adapter_for

ASSET_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bmp",
    ".css",
    ".doc",
    ".docx",
    ".eot",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".svg",
    ".tar",
    ".tiff",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
}

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}

TEMPLATE_TOKENS = (
    "${",
    "{{",
    "}}",
    "<%",
    "%>",
    "`",
)

GLOBAL_EXCLUDE_SIGNALS = (
    "/accessibility-statement",
    "/screen-reader",
    "/disclaimer",
    "/images/favico/manifest.json",
    "/manifest.json",
    "mailmodo",
    "activitysummary",
    "/privacy",
    "/terms",
    "/contact",
    "/login",
    "/logout",
    "forgot-password",
    "change-password",
)


def _contains_template_expression(value: str) -> bool:
    decoded = unquote(value).lower()
    return any(token in decoded for token in TEMPLATE_TOKENS)


def normalize_url(base_url: str, candidate: str) -> str | None:
    value = (candidate or "").strip()

    if not value:
        return None

    if value.startswith(("#", "javascript:", "mailto:", "tel:")):
        return None

    if _contains_template_expression(value):
        return None

    absolute = urljoin(base_url, value)

    if _contains_template_expression(absolute):
        return None

    parsed = urlsplit(absolute)

    if parsed.scheme.lower() not in {"http", "https"}:
        return None

    if not parsed.hostname:
        return None

    path = parsed.path or "/"
    normalized_path = posixpath.normpath(path)

    if path.endswith("/") and not normalized_path.endswith("/"):
        normalized_path += "/"

    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path

    filtered_query: list[tuple[str, str]] = []

    for key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        key_lower = key.lower()

        if key_lower.startswith("utm_"):
            continue

        if key_lower in TRACKING_QUERY_KEYS:
            continue

        if _contains_template_expression(key):
            continue

        if _contains_template_expression(query_value):
            continue

        filtered_query.append((key, query_value))

    filtered_query.sort()

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def domain_is_allowed(source: Source, url: str) -> bool:
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")

    allowed = {
        source.official_domain.lower().rstrip("."),
    }

    allowed.update(str(item).lower().rstrip(".") for item in source.allowed_domains)

    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed)


def candidate_is_allowed(
    source: Source,
    url: str,
    anchor_text: str = "",
) -> tuple[bool, str]:
    if not domain_is_allowed(source, url):
        return False, "outside registered source domains"

    if _contains_template_expression(url):
        return False, "unresolved template expression"

    decoded_url = unquote(url).lower()
    combined = f"{decoded_url} {anchor_text.lower()}"

    for signal in GLOBAL_EXCLUDE_SIGNALS:
        if signal in combined:
            return False, f"excluded non-content route: {signal}"

    path = urlsplit(url).path.lower()
    suffix = posixpath.splitext(path)[1]

    if suffix in ASSET_EXTENSIONS:
        return False, f"non-content asset extension: {suffix}"

    adapter = adapter_for(source.official_domain)

    for keyword in adapter["exclude_keywords"]:
        keyword_lower = str(keyword).lower()

        if keyword_lower in combined:
            return False, f"excluded keyword: {keyword}"

    return True, ""
