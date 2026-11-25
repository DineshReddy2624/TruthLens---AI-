"""Brave Search API client implementation."""

import logging
from urllib.parse import urlparse
import httpx
from app.services.search.base import BaseSearchClient, SearchResult

logger = logging.getLogger(__name__)


class BraveSearchClient(BaseSearchClient):
    """Brave Web Search API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            logger.warning("Brave search API key not configured; returning empty search results.")
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": max_results,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(self.api_url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("web", {}).get("results", []):
                url = item.get("url", "")
                domain = urlparse(url).netloc.lower().replace("www.", "")
                results.append(
                    SearchResult(
                        url=url,
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                        domain=domain,
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Brave search error for query '{query}': {e}")
            return []
