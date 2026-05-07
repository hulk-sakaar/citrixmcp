#!/usr/bin/env python3
import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

from .fetcher import CitrixFetcher
from .sitemap_index import SitemapIndex
from .tools.daas_api import register_daas_api
from .tools.docs import register_docs
from .tools.generic import register_generic

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def build_server() -> FastMCP:
    mcp = FastMCP("citrix-mcp")
    fetcher = CitrixFetcher()
    index = SitemapIndex()
    register_docs(mcp, fetcher, index)
    register_daas_api(mcp, fetcher, index)
    register_generic(mcp, fetcher)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="citrix-mcp — read-only MCP server for Citrix docs and DaaS API reference"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the HTTP page cache at ~/.cache/citrix-mcp/pages/",
    )
    parser.add_argument(
        "--refresh-index",
        action="store_true",
        help="Rebuild the sitemap FTS5 search index (one-time setup; takes a few minutes)",
    )
    args, _ = parser.parse_known_args()

    if args.clear_cache:
        CitrixFetcher().clear_cache()
        logger.info("Cache cleared")
        return

    if args.refresh_index:
        index = SitemapIndex()
        total = index.refresh()
        logger.info("Index rebuilt: %d pages indexed", total)

    mcp = build_server()
    logger.info("Starting citrix-mcp server")
    mcp.run()


if __name__ == "__main__":
    main()
