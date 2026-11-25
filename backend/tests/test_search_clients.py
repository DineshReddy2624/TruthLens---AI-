"""Unit tests for pluggable search clients (Tavily, SerpAPI, Brave, Mock)."""

import pytest
from app.services.search.base import SearchResult
from app.services.search.mock import MockSearchClient
from app.services.search.factory import get_search_client
from app.services.search.tavily import TavilySearchClient
from app.services.search.serpapi import SerpApiSearchClient
from app.services.search.brave import BraveSearchClient


class TestSearchClients:
    def test_mock_search_client_default(self):
        client = MockSearchClient()
        results = client.search("Great Wall of China visible from space", max_results=3)
        assert len(results) <= 3
        assert len(results) > 0
        assert any("nasa.gov" in r.url or "scientificamerican" in r.url for r in results)
        assert results[0].domain is not None
        assert client.recorded_queries[0] == "Great Wall of China visible from space"

    def test_mock_search_client_predefined(self):
        predefined = [
            SearchResult(
                url="https://example.com/study",
                title="Example Study",
                snippet="Evidence snippet text.",
                domain="example.com",
            )
        ]
        client = MockSearchClient(predefined_results=predefined)
        results = client.search("anything")
        assert len(results) == 1
        assert results[0].url == "https://example.com/study"

    def test_search_factory_returns_mock_when_no_key(self):
        client = get_search_client("tavily", api_key="")
        assert isinstance(client, MockSearchClient)

        client_serp = get_search_client("serpapi", api_key="")
        assert isinstance(client_serp, MockSearchClient)

        client_brave = get_search_client("brave", api_key="")
        assert isinstance(client_brave, MockSearchClient)

    def test_search_factory_returns_provider_when_key_given(self):
        client = get_search_client("tavily", api_key="test-key-123")
        assert isinstance(client, TavilySearchClient)

        client_serp = get_search_client("serpapi", api_key="test-key-123")
        assert isinstance(client_serp, SerpApiSearchClient)

        client_brave = get_search_client("brave", api_key="test-key-123")
        assert isinstance(client_brave, BraveSearchClient)
