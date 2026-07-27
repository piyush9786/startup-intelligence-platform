"""Tests for web search clients."""
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.research.services.brave_client import search_web_brave
from apps.research.services.search_provider import execute_web_search
from apps.research.services.tavily_client import WebSearchError, search_web


def test_tavily_client_missing_key(settings):
    settings.TAVILY_API_KEY = ""
    with pytest.raises(WebSearchError, match="TAVILY_API_KEY is not configured"):
        search_web("health tech startup India")


def test_tavily_client_mocked(settings):
    settings.TAVILY_API_KEY = "test-key"
    settings.WEB_SEARCH_DEPTH = "basic"
    settings.WEB_SEARCH_TIME_RANGE = "month"
    settings.WEB_SEARCH_START_DATE = ""
    settings.WEB_SEARCH_END_DATE = ""

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "HealthTech India",
                "url": "https://healthtech.in",
                "content": "Leading health tech startup",
                "score": 0.9,
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp) as post:
        results = search_web("health tech startup India")
        assert len(results) == 1
        assert results[0].url == "https://healthtech.in"
        assert post.call_args.kwargs["json"]["search_depth"] == "basic"
        assert post.call_args.kwargs["json"]["time_range"] == "month"


def test_brave_client_missing_key(settings):
    settings.BRAVE_API_KEY = ""
    with pytest.raises(WebSearchError, match="BRAVE_API_KEY is not configured"):
        search_web_brave("wearable medical devices")


def test_search_provider_rejects_unknown_provider(settings):
    settings.WEB_SEARCH_ENABLED = True
    settings.WEB_SEARCH_PROVIDER = "unknown-provider"

    with pytest.raises(ImproperlyConfigured, match="WEB_SEARCH_PROVIDER"):
        execute_web_search("health tech startup India")


def test_search_provider_reports_disabled_search(settings):
    settings.WEB_SEARCH_ENABLED = False

    with pytest.raises(WebSearchError, match="disabled"):
        execute_web_search("health tech startup India")
