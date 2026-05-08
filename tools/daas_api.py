import logging
from mcp.server.fastmcp import FastMCP
from ..cleaner import clean
from ..fetcher import CitrixFetcher, AllowlistError
from ..models import ApiEndpoint
from ..sitemap_index import SitemapIndex

logger = logging.getLogger(__name__)

_DAAS_HOST = "developer-docs.citrix.com"


def register_daas_api(mcp: FastMCP, fetcher: CitrixFetcher, index: SitemapIndex) -> None:

    @mcp.tool()
    def search_daas_api(query: str, limit: int = 10) -> list[dict]:
        """Search the Citrix DaaS REST API reference. Returns title and url per hit."""
        return [h.model_dump(mode="json") for h in index.search(query, host=_DAAS_HOST, limit=limit)]

    @mcp.tool()
    def get_daas_api_endpoint(endpoint_id_or_path: str) -> dict:
        """Fetch a Citrix DaaS REST API reference page. Accepts a full URL or searches by name/path fragment."""
        if endpoint_id_or_path.startswith("http"):
            url = endpoint_id_or_path
        else:
            hits = index.search(endpoint_id_or_path, host=_DAAS_HOST, limit=1)
            if not hits:
                return {"error": f"No API reference found for: {endpoint_id_or_path!r}"}
            url = hits[0].url
        try:
            raw = fetcher.fetch(url)
        except AllowlistError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Fetch failed: {exc}"}
        doc = clean(raw["html"], raw["url"])
        endpoint = ApiEndpoint(
            title=doc.title,
            url=doc.url,
            markdown=doc.markdown,
        )
        return endpoint.model_dump(mode="json")
