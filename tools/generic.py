import logging
from mcp.server.fastmcp import FastMCP
from ..cleaner import clean
from ..fetcher import CitrixFetcher, AllowlistError

logger = logging.getLogger(__name__)


def register_generic(mcp: FastMCP, fetcher: CitrixFetcher) -> None:

    @mcp.tool()
    def fetch_url(url: str) -> dict:
        """Fetch any allowlisted Citrix URL and return it as clean Markdown. Allowed hosts: docs.citrix.com, developer-docs.citrix.com, developer.cloud.com, www.citrix.com, community.citrix.com."""
        try:
            raw = fetcher.fetch(url)
        except AllowlistError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Fetch failed: {exc}"}
        doc = clean(raw["html"], raw["url"])
        return doc.model_dump(mode="json")
