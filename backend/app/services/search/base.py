"""Pluggable search API client interface and data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """Standardized search result across all search providers."""
    url: str
    title: str
    snippet: str
    published_date: Optional[str] = None
    domain: Optional[str] = None


class BaseSearchClient(ABC):
    """Abstract base class for search API providers."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Execute a web search and return standardized results."""
        pass
