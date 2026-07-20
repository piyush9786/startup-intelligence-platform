from __future__ import annotations

import re
from urllib.parse import urlsplit

from apps.discovery.models import DiscoveredURL

DETAIL_SIGNALS = {
    "scheme_detail": ["eligibility", "benefits", "how to apply", "documents required"],
    "loan_detail": ["loan amount", "interest rate", "repayment", "collateral"],
    "registration_detail": ["registration process", "register", "required documents", "validity"],
    "certificate_detail": ["certificate", "licence", "license", "renewal", "issuing authority"],
    "benefit_detail": ["tax benefit", "reimbursement", "exemption", "benefit"],
    "incubator_detail": ["incubator", "cohort", "mentorship", "apply"],
}
LOGIN_SIGNALS = ["login", "logout", "password", "otp", "sign in", "forgot password"]
LISTING_SIGNALS = ["all schemes", "schemes and policies", "scheme list", "explore schemes"]


def classify_page(
    *,
    url: str,
    title: str = "",
    text: str = "",
    anchor_text: str = "",
) -> str:
    lower_url = url.lower()
    path = urlsplit(url).path.lower()
    lower = f"{title}\n{text[:30000]}\n{anchor_text}".lower()

    if path.endswith(("sitemap.xml", "sitemap_index.xml")):
        return DiscoveredURL.PageType.SITEMAP
    if path.endswith(".pdf"):
        if "policy" in lower_url or "policy" in lower:
            return DiscoveredURL.PageType.POLICY_PDF
        return DiscoveredURL.PageType.GUIDELINE_PDF
    if any(signal in lower_url for signal in ["/api/", "api.", "graphql"]):
        return DiscoveredURL.PageType.API_ENDPOINT
    if any(signal in lower for signal in LOGIN_SIGNALS) and len(text.split()) < 1200:
        return DiscoveredURL.PageType.LOGIN
    if re.search(r"(?:^|/)(?:apply|application)(?:/|$)", path):
        return DiscoveredURL.PageType.APPLICATION_PAGE
    if path in {"", "/", "/index.html", "/index.htm"}:
        return DiscoveredURL.PageType.LANDING
    if any(signal in lower for signal in LISTING_SIGNALS) or any(
        signal in lower_url
        for signal in [
            "government-schemes",
            "schemes-and-policies",
            "scheme-list",
            "all-schemes",
        ]
    ):
        return DiscoveredURL.PageType.LISTING
    if "faq" in lower_url or "frequently asked" in lower:
        return DiscoveredURL.PageType.FAQ

    scores: dict[str, int] = {}
    for page_type, signals in DETAIL_SIGNALS.items():
        scores[page_type] = sum(1 for signal in signals if signal in lower)
    best_type = max(scores, key=scores.get)
    if scores[best_type] >= 3:
        return best_type

    detail_url_signals = [
        "/scheme/",
        "/schemes/",
        "scheme-details",
        "scheme_detail",
        "program-details",
        "programme-details",
        "startup-scheme",
        "scheme-guideline",
        "scheme-guidelines",
    ]
    if any(signal in lower_url for signal in detail_url_signals):
        return DiscoveredURL.PageType.SCHEME_DETAIL
    if any(word in lower_url for word in ["category", "sector", "ministry", "state"]):
        return DiscoveredURL.PageType.CATEGORY
    return DiscoveredURL.PageType.UNKNOWN
