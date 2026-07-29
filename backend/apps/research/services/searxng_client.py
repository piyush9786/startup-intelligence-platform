"""Self-hosted SearXNG web-search client."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .tavily_client import SearchResult, WebSearchError


def _normalise_score(value: object) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    return max(0.0, min(float(value), 1.0))


def _publisher_from_url(url: str) -> str | None:
    hostname = (urlparse(url).hostname or "").lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname or None


def _domain_allowed(
    url: str,
    include_domains: list[str] | None,
) -> bool:
    if not include_domains:
        return True

    hostname = (urlparse(url).hostname or "").lower()

    for domain in include_domains:
        clean_domain = domain.lower().strip().lstrip(".")

        if hostname == clean_domain:
            return True

        if hostname.endswith(f".{clean_domain}"):
            return True

    return False


def search_web_searxng(
    query: str,
    *,
    max_results: int = 8,
    include_domains: list[str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> list[SearchResult]:
    """Search through the project's private SearXNG instance."""

    clean_query = " ".join(query.split())

    if not clean_query:
        raise WebSearchError("A search query is required.")

    base_url = str(
        getattr(
            settings,
            "SEARXNG_BASE_URL",
            "http://searxng:8080",
        )
    ).strip().rstrip("/")

    if not base_url:
        raise ImproperlyConfigured(
            "SEARXNG_BASE_URL is not configured."
        )

    limit = min(max(int(max_results), 1), 20)

    language = str(
        getattr(settings, "SEARXNG_LANGUAGE", "en")
    ).strip()

    categories = str(
        getattr(settings, "SEARXNG_CATEGORIES", "general")
    ).strip()

    safe_search = int(
        getattr(settings, "SEARXNG_SAFE_SEARCH", 1)
    )

    params: dict[str, str | int] = {
        "q": clean_query,
        "format": "json",
        "language": language or "en",
        "categories": categories or "general",
        "safesearch": max(0, min(safe_search, 2)),
        "pageno": 1,
    }

    time_range = str(
        getattr(settings, "WEB_SEARCH_TIME_RANGE", "")
    ).strip()

    if time_range:
        params["time_range"] = time_range

    timeout_seconds = float(
        getattr(settings, "WEB_SEARCH_TIMEOUT_SECONDS", 30)
    )

    user_agent = str(
        getattr(
            settings,
            "COLLECTOR_USER_AGENT",
            "StartupIntelligenceCollector/1.0",
        )
    )

    try:
        with httpx.Client(
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=min(10.0, timeout_seconds),
            ),
            follow_redirects=True,
            transport=transport,
            headers={
                "Accept": "application/json",
                "User-Agent": user_agent,
            },
        ) as client:
            response = client.get(
                f"{base_url}/search",
                params=params,
            )
            response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise WebSearchError(
            "The SearXNG search request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            raise WebSearchError(
                "SearXNG rejected JSON output. Ensure json is "
                "enabled under search.formats."
            ) from exc

        raise WebSearchError(
            "SearXNG returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.HTTPError as exc:
        raise WebSearchError(
            "The SearXNG search request failed."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise WebSearchError(
            "SearXNG returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise WebSearchError(
            "SearXNG returned an invalid response object."
        )

    raw_results = payload.get("results", [])

    if not isinstance(raw_results, list):
        raise WebSearchError(
            "SearXNG returned an invalid results collection."
        )

    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()

        parsed_url = urlparse(url)

        if parsed_url.scheme not in {"http", "https"}:
            continue

        if not parsed_url.netloc or not title:
            continue

        if not _domain_allowed(url, include_domains):
            continue

        canonical_url = url.split("#", 1)[0]

        if canonical_url in seen_urls:
            continue

        seen_urls.add(canonical_url)

        published_at = (
            item.get("publishedDate")
            or item.get("published_date")
            or item.get("published_at")
        )

        publisher = (
            item.get("publisher")
            or item.get("source")
            or _publisher_from_url(url)
        )

        results.append(
            SearchResult(
                title=title,
                url=canonical_url,
                content=content,
                score=_normalise_score(item.get("score")),
                published_at=(
                    str(published_at)
                    if published_at
                    else None
                ),
                publisher=(
                    str(publisher)
                    if publisher
                    else None
                ),
            )
        )

        if len(results) >= limit:
            break

    return results
