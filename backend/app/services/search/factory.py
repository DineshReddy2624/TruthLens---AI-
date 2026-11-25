"""Factory to obtain the configured search API client."""

from app.config import get_settings
from app.services.search.base import BaseSearchClient
from app.services.search.tavily import TavilySearchClient
from app.services.search.serpapi import SerpApiSearchClient
from app.services.search.brave import BraveSearchClient
from app.services.search.mock import MockSearchClient


def get_search_client(provider: str | None = None, api_key: str | None = None) -> BaseSearchClient:
    """Return an instantiated search client based on settings or explicit provider parameter."""
    settings = get_settings()
    active_provider = (provider or settings.SEARCH_PROVIDER or "mock").lower()
    key = api_key if api_key is not None else settings.SEARCH_API_KEY

    if active_provider == "tavily":
        if not key or key == "your-search-api-key-here" or "your-" in key:
            return MockSearchClient()
        return TavilySearchClient(api_key=key)
    elif active_provider == "serpapi":
        if not key or key == "your-search-api-key-here" or "your-" in key:
            return MockSearchClient()
        return SerpApiSearchClient(api_key=key)
    elif active_provider == "brave":
        if not key or key == "your-search-api-key-here" or "your-" in key:
            return MockSearchClient()
        return BraveSearchClient(api_key=key)
    else:
        return MockSearchClient()
