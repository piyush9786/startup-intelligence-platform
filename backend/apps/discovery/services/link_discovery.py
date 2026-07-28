from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from apps.discovery.models import DiscoveredURL
from apps.sources.models import Source

from .adapters import adapter_for
from .classifier import classify_page
from .url_tools import candidate_is_allowed, normalize_url

URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", flags=re.IGNORECASE)


@dataclass(frozen=True)
class LinkCandidate:
    original_url: str
    normalized_url: str
    anchor_text: str
    page_type: str
    discovery_method: str
    priority: int
    allowed: bool
    rejection_reason: str
    signals: dict[str, Any]


def _priority(page_type: str, combined: str) -> int:
    priorities = {
        DiscoveredURL.PageType.SCHEME_DETAIL: 10,
        DiscoveredURL.PageType.LOAN_DETAIL: 10,
        DiscoveredURL.PageType.REGISTRATION_DETAIL: 12,
        DiscoveredURL.PageType.CERTIFICATE_DETAIL: 12,
        DiscoveredURL.PageType.BENEFIT_DETAIL: 12,
        DiscoveredURL.PageType.GUIDELINE_PDF: 15,
        DiscoveredURL.PageType.POLICY_PDF: 18,
        DiscoveredURL.PageType.APPLICATION_PAGE: 20,
        DiscoveredURL.PageType.LISTING: 30,
        DiscoveredURL.PageType.CATEGORY: 35,
        DiscoveredURL.PageType.SITEMAP: 5,
        DiscoveredURL.PageType.API_ENDPOINT: 70,
        DiscoveredURL.PageType.FAQ: 45,
        DiscoveredURL.PageType.UNKNOWN: 60,
        DiscoveredURL.PageType.LOGIN: 100,
        DiscoveredURL.PageType.ASSET: 100,
    }
    score = priorities.get(page_type, 60)

    if page_type == DiscoveredURL.PageType.API_ENDPOINT:
        useful_api_signals = (
            "scheme",
            "grant",
            "loan",
            "funding",
            "benefit",
            "eligibility",
            "programme",
            "program",
        )
        if any(signal in combined for signal in useful_api_signals):
            score = 25
        else:
            score = 70

    for keyword in ("eligibility", "benefit", "apply", "guideline", "scheme"):
        if keyword in combined:
            score = max(1, score - 2)
    return score


def discover_links(
    *,
    source: Source,
    parent_url: str,
    content: bytes,
) -> list[LinkCandidate]:
    soup = BeautifulSoup(content, "html.parser")
    raw_candidates: list[tuple[str, str, str]] = []

    for element in soup.find_all(["a", "iframe", "link"]):
        href = element.get("href") or element.get("src")
        if not href:
            continue
        anchor = " ".join(element.get_text(" ", strip=True).split())[:1000]
        method = (
            DiscoveredURL.DiscoveryMethod.PDF_LINK
            if str(href).lower().split("?", 1)[0].endswith(".pdf")
            else DiscoveredURL.DiscoveryMethod.HTML_LINK
        )
        raw_candidates.append((str(href), anchor, method))

    for element in soup.find_all(True):
        for attribute in ("data-href", "data-url", "data-link", "data-api"):
            value = element.get(attribute)
            if value:
                raw_candidates.append(
                    (
                        str(value),
                        " ".join(element.get_text(" ", strip=True).split())[:1000],
                        DiscoveredURL.DiscoveryMethod.EMBEDDED_JSON,
                    )
                )

    for script in soup.find_all("script"):
        script_text = script.string or script.get_text(" ", strip=True)
        if not script_text:
            continue
        if script.get("type") in {"application/ld+json", "application/json"}:
            try:
                serialized = json.dumps(json.loads(script_text), ensure_ascii=False)
            except (TypeError, ValueError):
                serialized = script_text
        else:
            serialized = script_text
        for value in URL_PATTERN.findall(serialized[:2_000_000]):
            raw_candidates.append(
                (value.rstrip(".,);]"), "", DiscoveredURL.DiscoveryMethod.EMBEDDED_JSON)
            )

    adapter = adapter_for(source.official_domain)
    include_keywords = [str(item).lower() for item in adapter["include_keywords"]]
    discovered: dict[str, LinkCandidate] = {}
    for original, anchor_text, method in raw_candidates:
        normalized = normalize_url(parent_url, original)
        if not normalized:
            continue
        allowed, reason = candidate_is_allowed(source, normalized, anchor_text)
        if not allowed and reason.startswith("non-content asset extension"):
            continue
        combined = f"{normalized} {anchor_text}".lower()
        page_type = classify_page(
            url=normalized,
            anchor_text=anchor_text,
        )
        include_matches = [keyword for keyword in include_keywords if keyword in combined]
        if not include_matches and page_type == DiscoveredURL.PageType.UNKNOWN:
            allowed = False
            reason = reason or "no startup-domain discovery signal"

        candidate = LinkCandidate(
            original_url=original,
            normalized_url=normalized,
            anchor_text=anchor_text,
            page_type=page_type,
            discovery_method=method,
            priority=_priority(page_type, combined),
            allowed=allowed,
            rejection_reason=reason,
            signals={"include_keywords": include_matches},
        )
        previous = discovered.get(normalized)
        if previous is None or candidate.priority < previous.priority:
            discovered[normalized] = candidate
    return sorted(discovered.values(), key=lambda item: item.priority)
