import logging
from urllib.parse import quote_plus

from mcp.server.fastmcp import FastMCP
from ..cleaner import clean
from ..fetcher import CitrixFetcher, AllowlistError
from ..models import SearchHit

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

    @mcp.tool()
    def search_community(query: str, limit: int = 10) -> list[dict]:
        """Search the Citrix Community (community.citrix.com) across all content types: forums, tech zone, blogs, events, and documents. Returns title, url, and snippet per result."""
        import re
        from bs4 import BeautifulSoup

        search_url = f"https://community.citrix.com/search/?q={quote_plus(query).replace('+', '%20')}&sortby=relevancy"
        try:
            raw = fetcher.fetch(search_url)
        except AllowlistError as exc:
            return [{"error": str(exc)}]
        except Exception as exc:
            return [{"error": f"Fetch failed: {exc}"}]

        soup = BeautifulSoup(raw["html"], "lxml")
        results: list[dict] = []
        seen_urls: set[str] = set()

        # Content URL pattern — matches actual articles, topics, and blog posts (not category index pages)
        content_pattern = re.compile(
            r"community\.citrix\.com/"
            r"(forums/topic/|"
            r"tech-zone/(design|learn|build)/(design-decisions|tech-briefs|tech-insights|reference-architectures|deployment-guides|tech-papers|poc-guides)/[^/]+/|"
            r"techzone-blogs/[^/]+/[^/]+/)"
        )

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            if not content_pattern.search(href):
                continue
            # Skip breadcrumbs and nav
            parent = a.parent
            if parent:
                parent_classes = " ".join(parent.get("class", []))
                if "breadcrumb" in parent_classes or "nav" in parent_classes:
                    continue
            # Deduplicate
            clean_url = href.split("?")[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            # Try to get snippet from nearby text
            snippet = ""
            sibling = a.find_next(string=True)
            if sibling and len(sibling.strip()) > 20:
                snippet = sibling.strip()[:200]

            results.append({"title": text, "url": href, "snippet": snippet})
            if len(results) >= limit:
                break

        return results
