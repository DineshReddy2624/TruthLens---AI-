"""SerpAPI search client implementation."""

import logging
from urllib.parse import urlparse
import httpx
from app.services.search.base import BaseSearchClient, SearchResult

logger = logging.getLogger(__name__)


class SerpApiSearchClient(BaseSearchClient):
    """SerpAPI Google Search client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://serpapi.com/search.json"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            logger.warning("SerpAPI key not configured; returning empty search results.")
            return []

        params = {
            "api_key": self.api_key,
            "q": query,
            "num": max_results,
            "engine": "google",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(self.api_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", []):
                url = item.get("link", "")
                domain = urlparse(url).netloc.lower().replace("www.", "")
                results.append(
                    SearchResult(
                        url=url,
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        domain=domain,
                    )
                )
            return results
        except Exception as e:
            logger.error(f"SerpAPI search error for query '{query}': {e}")
            return []
