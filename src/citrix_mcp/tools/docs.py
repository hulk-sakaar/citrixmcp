import logging
from mcp.server.fastmcp import FastMCP
from ..cleaner import clean
from ..fetcher import CitrixFetcher, AllowlistError
from ..sitemap_index import SitemapIndex

logger = logging.getLogger(__name__)


def register_docs(mcp: FastMCP, fetcher: CitrixFetcher, index: SitemapIndex) -> None:

    @mcp.tool()
    def search_citrix_docs(query: str, product: str | None = None, limit: int = 10) -> list[dict]:
        """Search Citrix product documentation. Optionally filter by product slug (e.g. 'citrix-daas'). Returns title, url, product per hit."""
        return [h.model_dump(mode="json") for h in index.search(query, product=product, host="docs.citrix.com", limit=limit)]

    @mcp.tool()
    def fetch_citrix_doc(url: str) -> dict:
        """Fetch a docs.citrix.com page and return it as clean Markdown. Strips nav, feedback widgets, and translation banners."""
        try:
            raw = fetcher.fetch(url)
        except AllowlistError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Fetch failed: {exc}"}
        doc = clean(raw["html"], raw["url"])
        return doc.model_dump(mode="json")

    @mcp.tool()
    def list_citrix_products() -> list[dict]:
        """List all Citrix product areas available in the documentation index."""
        products = [p for p in index.list_products() if p.url_prefix.startswith("https://docs.citrix.com/")]
        return [p.model_dump(mode="json") for p in products]
