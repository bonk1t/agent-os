from agency_swarm.tools import BaseTool
from duckduckgo_search import DDGS
from pydantic import Field


class SearchWeb(BaseTool):
    """Search the web with a search query and return the results."""

    query: str = Field(
        ...,
        description="The search query you want to use. Optimize the search query for an internet search engine.",
    )
    max_results: int = Field(default=10, description="The maximum number of search results to return, default is 10.")

    def run(self) -> str:
        with DDGS() as ddgs:
            results = [str(r) for r in ddgs.text(self.query, max_results=self.max_results)]
            return "\n".join(results) if results else "No results found."
