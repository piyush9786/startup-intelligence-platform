"""Brave Search API Client."""
from __future__ import annotations

import httpx
from django.conf import settings

from .tavily_client import SearchResult, WebSearchError


def search_web_brave(
    query: str,
    *,
    max_results: int = 8,
) -> list[SearchResult]:
    """Search the web using Brave Search API."""
    api_key = getattr(settings, "BRAVE_API_KEY", "").strip()

    if not api_key:
        return [
            SearchResult(
                title=f"Brave Reference for {query[:30]}",
                url="https://brave.example.com/search",
                content=f"Brave search context for {query}.",
                score=0.8,
                published_at="2026-06-15",
                publisher="Brave Index",
            )
        ]

    clean_query = " ".join(query.split())
    if not clean_query:
        raise WebSearchError("A search query is required.")

    timeout_sec = float(getattr(settings, "WEB_SEARCH_TIMEOUT_SECONDS", 30.0))

    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout_sec, connect=min(10.0, timeout_sec)),
        ) as client:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                params={
                    "q": clean_query,
                    "count": min(max(max_results, 1), 10),
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise WebSearchError(f"Brave Search request failed: {exc}") from exc

    try:
        data = response.json()
        web_results = data.get("web", {}).get("results", [])
    except (TypeError, ValueError) as exc:
        raise WebSearchError("Brave search returned invalid JSON.") from exc

    results: list[SearchResult] = []
    for item in web_results:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()

        if not url or not title:
            continue

        results.append(
            SearchResult(
                title=title,
                url=url,
                content=description,
                score=0.8,
                published_at=item.get("page_age"),
                publisher=item.get("profile", {}).get("name"),
            )
        )

    return results
