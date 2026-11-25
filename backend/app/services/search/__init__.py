"""Pluggable search API module."""

from app.services.search.base import BaseSearchClient, SearchResult
from app.services.search.factory import get_search_client
from app.services.search.mock import MockSearchClient

__all__ = ["BaseSearchClient", "SearchResult", "get_search_client", "MockSearchClient"]
