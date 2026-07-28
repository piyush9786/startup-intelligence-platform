"""Tavily Web Search Client."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class WebSearchError(RuntimeError):
    """Raised when the configured web-search service fails."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str
    score: float | None
    published_at: str | None
    publisher: str | None = None


def search_web(
    query: str,
    *,
    max_results: int = 8,
    include_domains: list[str] | None = None,
) -> list[SearchResult]:
    """Search the web using Tavily API."""
    api_key = getattr(settings, "TAVILY_API_KEY", "").strip()

    if not api_key:
        raise WebSearchError("TAVILY_API_KEY is not configured in backend environment.")

    clean_query = " ".join(query.split())

    if not clean_query:
        raise WebSearchError("A search query is required.")

    search_depth = str(getattr(settings, "WEB_SEARCH_DEPTH", "basic")).strip()
    allowed_depths = {"basic", "advanced", "fast", "ultra-fast"}
    if search_depth not in allowed_depths:
        raise ImproperlyConfigured(
            f"WEB_SEARCH_DEPTH must be one of {sorted(allowed_depths)}."
        )

    time_range = str(getattr(settings, "WEB_SEARCH_TIME_RANGE", "")).strip()
    if time_range and time_range not in {"day", "week", "month", "year"}:
        raise ImproperlyConfigured(
            "WEB_SEARCH_TIME_RANGE must be day, week, month, year, or blank."
        )
    start_date = str(getattr(settings, "WEB_SEARCH_START_DATE", "")).strip()
    end_date = str(getattr(settings, "WEB_SEARCH_END_DATE", "")).strip()
    for setting_name, value in (
        ("WEB_SEARCH_START_DATE", start_date),
        ("WEB_SEARCH_END_DATE", end_date),
    ):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ImproperlyConfigured(
                    f"{setting_name} must use YYYY-MM-DD."
                ) from exc

    payload: dict[str, Any] = {
        "query": clean_query,
        "search_depth": search_depth,
        "max_results": min(max(max_results, 1), 10),
        "include_answer": False,
        "include_raw_content": False,
    }

    if include_domains:
        payload["include_domains"] = include_domains
    if start_date or end_date:
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
    elif time_range:
        payload["time_range"] = time_range

    timeout_sec = float(getattr(settings, "WEB_SEARCH_TIMEOUT_SECONDS", 30.0))

    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout_sec, connect=min(10.0, timeout_sec)),
        ) as client:
            response = client.post(
                "https://api.tavily.com/search",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise WebSearchError("The web search request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise WebSearchError(
            f"The web search provider returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise WebSearchError("The web search request failed.") from exc

    try:
        data = response.json()
        raw_results = data.get("results", [])
    except (TypeError, ValueError) as exc:
        raise WebSearchError(
            "The web search provider returned invalid JSON."
        ) from exc

    results: list[SearchResult] = []

    for item in raw_results:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()

        if not url or not title:
            continue

        score = item.get("score")
        publisher = item.get("publisher") or item.get("source")

        results.append(
            SearchResult(
                title=title,
                url=url,
                content=content,
                score=float(score) if isinstance(score, int | float) else None,
                published_at=item.get("published_date"),
                publisher=str(publisher) if publisher else None,
            )
        )

    return results
