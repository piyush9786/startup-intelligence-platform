"""Unified Web Search Provider Router with Caching."""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from .brave_client import search_web_brave
from .tavily_client import SearchResult, WebSearchError, search_web

logger = logging.getLogger(__name__)


def execute_web_search(
    query: str,
    *,
    max_results: int | None = None,
) -> list[SearchResult]:
    """Execute web search using the configured provider (tavily or brave) with Redis caching."""
    if not getattr(settings, "WEB_SEARCH_ENABLED", True):
        raise WebSearchError("Web search is disabled by configuration.")

    provider = str(getattr(settings, "WEB_SEARCH_PROVIDER", "tavily")).lower().strip()
    if provider not in {"tavily", "brave"}:
        raise ImproperlyConfigured(
            "WEB_SEARCH_PROVIDER must be either 'tavily' or 'brave'."
        )
    limit = max_results or int(getattr(settings, "WEB_SEARCH_MAX_RESULTS", 8))
    cache_ttl = int(getattr(settings, "WEB_SEARCH_CACHE_SECONDS", 21600))
    search_depth = str(getattr(settings, "WEB_SEARCH_DEPTH", "basic"))
    time_range = str(getattr(settings, "WEB_SEARCH_TIME_RANGE", ""))
    start_date = str(getattr(settings, "WEB_SEARCH_START_DATE", ""))
    end_date = str(getattr(settings, "WEB_SEARCH_END_DATE", ""))

    clean_query = " ".join(query.split())
    if not clean_query:
        return []

    # Redis cache check
    query_hash = hashlib.sha256(clean_query.casefold().encode()).hexdigest()
    option_hash = hashlib.sha256(
        f"{search_depth}:{time_range}:{start_date}:{end_date}".encode()
    ).hexdigest()[:16]
    cache_key = f"web_search:{provider}:{limit}:{option_hash}:{query_hash}"

    cached_results = cache.get(cache_key)
    if cached_results is not None:
        logger.info("Returning cached search results for query %r (provider=%s)", clean_query, provider)
        return cached_results

    if provider == "brave":
        results = search_web_brave(clean_query, max_results=limit)
    else:
        results = search_web(clean_query, max_results=limit)

    if results and cache_ttl > 0:
        cache.set(cache_key, results, cache_ttl)

    return results
