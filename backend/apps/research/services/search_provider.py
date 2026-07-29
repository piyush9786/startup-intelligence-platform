"""Unified web-search provider router with Redis caching."""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from .brave_client import search_web_brave
from .searxng_client import search_web_searxng
from .tavily_client import (
    SearchResult,
    WebSearchError,
    search_web,
)

logger = logging.getLogger(__name__)

SUPPORTED_SEARCH_PROVIDERS = {
    "searxng",
    "tavily",
    "brave",
}


def execute_web_search(
    query: str,
    *,
    max_results: int | None = None,
) -> list[SearchResult]:
    """Execute search through the configured provider."""

    if not getattr(settings, "WEB_SEARCH_ENABLED", True):
        raise WebSearchError(
            "Web search is disabled by configuration."
        )

    provider = str(
        getattr(
            settings,
            "WEB_SEARCH_PROVIDER",
            "searxng",
        )
    ).lower().strip()

    if provider not in SUPPORTED_SEARCH_PROVIDERS:
        supported = ", ".join(
            sorted(SUPPORTED_SEARCH_PROVIDERS)
        )
        raise ImproperlyConfigured(
            f"WEB_SEARCH_PROVIDER must be one of: {supported}."
        )

    limit = max_results or int(
        getattr(settings, "WEB_SEARCH_MAX_RESULTS", 8)
    )

    cache_ttl = int(
        getattr(
            settings,
            "WEB_SEARCH_CACHE_SECONDS",
            21600,
        )
    )

    search_depth = str(
        getattr(settings, "WEB_SEARCH_DEPTH", "basic")
    )

    time_range = str(
        getattr(settings, "WEB_SEARCH_TIME_RANGE", "")
    )

    start_date = str(
        getattr(settings, "WEB_SEARCH_START_DATE", "")
    )

    end_date = str(
        getattr(settings, "WEB_SEARCH_END_DATE", "")
    )

    searxng_language = str(
        getattr(settings, "SEARXNG_LANGUAGE", "en")
    )

    searxng_categories = str(
        getattr(
            settings,
            "SEARXNG_CATEGORIES",
            "general",
        )
    )

    searxng_safe_search = str(
        getattr(settings, "SEARXNG_SAFE_SEARCH", 1)
    )

    clean_query = " ".join(query.split())

    if not clean_query:
        return []

    query_hash = hashlib.sha256(
        clean_query.casefold().encode()
    ).hexdigest()

    option_string = ":".join(
        [
            search_depth,
            time_range,
            start_date,
            end_date,
            searxng_language,
            searxng_categories,
            searxng_safe_search,
        ]
    )

    option_hash = hashlib.sha256(
        option_string.encode()
    ).hexdigest()[:16]

    cache_key = (
        f"web_search:{provider}:{limit}:"
        f"{option_hash}:{query_hash}"
    )

    cached_results = cache.get(cache_key)

    if cached_results is not None:
        logger.info(
            "Returning cached search results for query %r "
            "(provider=%s)",
            clean_query,
            provider,
        )
        return cached_results

    if provider == "searxng":
        results = search_web_searxng(
            clean_query,
            max_results=limit,
        )
    elif provider == "brave":
        results = search_web_brave(
            clean_query,
            max_results=limit,
        )
    else:
        results = search_web(
            clean_query,
            max_results=limit,
        )

    if results and cache_ttl > 0:
        cache.set(
            cache_key,
            results,
            cache_ttl,
        )

    return results
