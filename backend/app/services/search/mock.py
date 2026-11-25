"""Mock search client for testing and offline development."""

from urllib.parse import urlparse
from app.services.search.base import BaseSearchClient, SearchResult


class MockSearchClient(BaseSearchClient):
    """Mock search client returning pre-configured or synthetic evidence results."""

    def __init__(self, predefined_results: list[SearchResult] | None = None):
        self.predefined_results = predefined_results or []
        self.recorded_queries: list[str] = []

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.recorded_queries.append(query)
        if self.predefined_results:
            return self.predefined_results[:max_results]

        # Generate synthetic contextual search results based on query terms
        clean_q = query.lower()
        if "great wall" in clean_q or "china" in clean_q:
            return [
                SearchResult(
                    url="https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
                    title="NASA - China's Wall Less Great in View from Space",
                    snippet="NASA astronauts and ISS photography confirm that the Great Wall of China is practically invisible from low Earth orbit without binoculars or telephoto lenses because its materials blend in with the surrounding terrain and its width is only a few meters.",
                    domain="nasa.gov",
                    published_date="2005-05-09",
                ),
                SearchResult(
                    url="https://www.scientificamerican.com/article/is-chinas-great-wall-visible-from-space/",
                    title="Is China's Great Wall Really Visible from Space? - Scientific American",
                    snippet="Optical physics proves that the human eye's angular resolution cannot resolve a structure only a few meters wide from a low Earth orbit of 160-300 km altitude.",
                    domain="scientificamerican.com",
                    published_date="2008-02-21",
                ),
                SearchResult(
                    url="https://en.wikipedia.org/wiki/Great_Wall_of_China",
                    title="Great Wall of China - Wikipedia",
                    snippet="A comprehensive archaeological survey using advanced technologies concluded that the Ming walls measure 8,850 km, while all dynasties combined built 21,196 km (13,171 miles).",
                    domain="wikipedia.org",
                    published_date="2024-01-15",
                ),
            ][:max_results]

        # General queries fallback: return at least 2 independent authoritative sources
        clean_name = "".join(c if c.isalnum() else " " for c in query).strip()[:40]
        q_slug = clean_name.lower().replace(" ", "_")

        return [
            SearchResult(
                url=f"https://en.wikipedia.org/wiki/{q_slug}",
                title=f"{clean_name} - Reference Overview",
                snippet=f"Technical records and historical documentation regarding {query}. Documented evidence indicates that {query} is documented in official archives.",
                domain="wikipedia.org",
                published_date="2024-01-15",
            ),
            SearchResult(
                url=f"https://www.reuters.com/fact-check/{q_slug}",
                title=f"Reuters Fact Check: Analysis of {clean_name}",
                snippet=f"Authoritative reports and industry investigations evaluate statements concerning {query}. Official publications confirm the factual background.",
                domain="reuters.com",
                published_date="2024-02-01",
            ),
        ][:max_results]
