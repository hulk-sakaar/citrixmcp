import logging
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import ALLOWED_HOSTS, CACHE_DIR, USER_AGENT
from .models import ProductInfo, SearchHit

logger = logging.getLogger(__name__)

_DB_FILE = "sitemap.db"
_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

_SITEMAP_ROOTS = [
    "https://docs.citrix.com/sitemap.xml",
    "https://developer-docs.citrix.com/sitemap.xml",
]

_CREATE_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
    url UNINDEXED,
    title,
    product,
    host UNINDEXED,
    last_modified UNINDEXED,
    tokenize='porter unicode61'
);
"""


def _slug_title(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else url
    return slug.replace("-", " ").replace("_", " ").title()


def _product_from_url(url: str) -> str:
    path = urlparse(url).path  # e.g. /en-us/citrix-daas/install-configure.html
    parts = [p for p in path.split("/") if p]
    # For docs.citrix.com: /en-us/<product>/...  → parts[1]
    # For developer-docs.citrix.com: /en-us/<product>/... or /projects/<product>/... → parts[1]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else urlparse(url).hostname or url


class SitemapIndex:
    def __init__(self, db_dir: Path | None = None):
        self._db_path = (db_dir or CACHE_DIR) / _DB_FILE
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute(_CREATE_TABLE)
        conn.commit()
        return conn

    def _fetch_xml(self, url: str) -> ET.Element | None:
        try:
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=30,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return ET.fromstring(response.text)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return None

    def refresh(self, product: str | None = None) -> int:
        """Crawl sitemaps and (re)populate the FTS5 index. Returns total pages indexed."""
        conn = self._connect()
        if product:
            conn.execute("DELETE FROM pages WHERE product = ?", (product,))
        else:
            conn.execute("DELETE FROM pages")
        conn.commit()
        total = 0
        for root_url in _SITEMAP_ROOTS:
            root = self._fetch_xml(root_url)
            if root is None:
                continue
            host = urlparse(root_url).hostname or ""
            # Collect sub-sitemap URLs
            sub_urls: list[str] = []
            for sitemap_el in root.findall("sm:sitemap", _NS):
                loc = sitemap_el.findtext("sm:loc", namespaces=_NS)
                if loc:
                    sub_urls.append(loc.strip())
            # If the root is itself a urlset (no sub-sitemaps), treat it as one
            if not sub_urls:
                sub_urls = [root_url]
            for sub_url in sub_urls:
                if urlparse(sub_url).hostname not in ALLOWED_HOSTS:
                    logger.warning("Skipping sub-sitemap outside allowlist: %s", sub_url)
                    continue
                parsed_product = _product_from_url(sub_url)
                if product and parsed_product != product:
                    continue
                if sub_url == root_url:
                    sub_root = root
                else:
                    sub_root = self._fetch_xml(sub_url)
                if sub_root is None:
                    continue
                rows = []
                for url_el in sub_root.findall("sm:url", _NS):
                    loc = url_el.findtext("sm:loc", namespaces=_NS)
                    if not loc:
                        continue
                    loc = loc.strip()
                    lastmod = url_el.findtext("sm:lastmod", namespaces=_NS) or ""
                    rows.append((
                        loc,
                        _slug_title(loc),
                        _product_from_url(loc),
                        urlparse(loc).hostname or host,
                        lastmod,
                    ))
                if rows:
                    conn.executemany(
                        "INSERT INTO pages(url, title, product, host, last_modified) VALUES (?,?,?,?,?)",
                        rows,
                    )
                    conn.commit()
                    total += len(rows)
                    logger.info("Indexed %d pages from %s", len(rows), sub_url)
        conn.close()
        return total

    def search(
        self,
        query: str,
        product: str | None = None,
        host: str | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        conn = self._connect()
        try:
            params: list = [query]
            where_clauses = ["pages MATCH ?"]
            if product:
                where_clauses.append("product = ?")
                params.append(product)
            if host:
                where_clauses.append("host = ?")
                params.append(host)
            params.append(limit)
            sql = f"SELECT url, title, product FROM pages WHERE {' AND '.join(where_clauses)} ORDER BY rank LIMIT ?"
            rows = conn.execute(sql, params).fetchall()
            return [SearchHit(url=r[0], title=r[1], product=r[2]) for r in rows]
        except sqlite3.OperationalError as exc:
            logger.warning("FTS search error: %s", exc)
            return []
        finally:
            conn.close()

    def list_products(self) -> list[ProductInfo]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT product, MIN(url), COUNT(*) FROM pages GROUP BY product ORDER BY product"
            ).fetchall()
            return [
                ProductInfo(
                    product=r[0],
                    url_prefix=r[1].rsplit("/", 1)[0] + "/",
                    page_count=r[2],
                )
                for r in rows
            ]
        except sqlite3.OperationalError as exc:
            logger.warning("list_products error: %s", exc)
            return []
        finally:
            conn.close()
