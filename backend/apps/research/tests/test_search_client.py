"""Tests for web search clients."""
from apps.research.services.brave_client import search_web_brave
from apps.research.services.tavily_client import search_web


def test_tavily_client_fallback():
    results = search_web("health tech startup India")
    assert len(results) > 0
    assert results[0].url != ""


def test_brave_client_fallback():
    results = search_web_brave("wearable medical devices")
    assert len(results) > 0
    assert results[0].title != ""
