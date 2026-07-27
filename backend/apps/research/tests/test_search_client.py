"""Tests for web search clients."""
from unittest.mock import MagicMock, patch

import pytest

from apps.research.services.brave_client import search_web_brave
from apps.research.services.tavily_client import WebSearchError, search_web


def test_tavily_client_missing_key(settings):
    settings.TAVILY_API_KEY = ""
    with pytest.raises(WebSearchError, match="TAVILY_API_KEY is not configured"):
        search_web("health tech startup India")


def test_tavily_client_mocked(settings):
    settings.TAVILY_API_KEY = "test-key"

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

    with patch("httpx.Client.post", return_value=mock_resp):
        results = search_web("health tech startup India")
        assert len(results) == 1
        assert results[0].url == "https://healthtech.in"


def test_brave_client_missing_key(settings):
    settings.BRAVE_API_KEY = ""
    with pytest.raises(WebSearchError, match="BRAVE_API_KEY is not configured"):
        search_web_brave("wearable medical devices")
