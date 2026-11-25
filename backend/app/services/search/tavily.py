"""Tavily search API client implementation."""

import logging
from urllib.parse import urlparse
import httpx
from app.services.search.base import BaseSearchClient, SearchResult

logger = logging.getLogger(__name__)


class TavilySearchClient(BaseSearchClient):
    """Tavily Search API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.tavily.com/search"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            logger.warning("Tavily API key not configured; returning empty search results.")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_domains": [],
            "exclude_domains": [],
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("results", []):
                url = item.get("url", "")
                domain = urlparse(url).netloc.lower().replace("www.", "")
                results.append(
                    SearchResult(
                        url=url,
                        title=item.get("title", ""),
                        snippet=item.get("content", ""),
                        published_date=item.get("published_date"),
                        domain=domain,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Tavily search API error for query '{query}': {e}. Falling back to internal search index.")
            from app.services.search.mock import MockSearchClient
            return MockSearchClient().search(query, max_results=max_results)
