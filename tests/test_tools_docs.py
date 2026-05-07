import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from citrix_mcp.tools.docs import register_docs
from mcp.server.fastmcp import FastMCP


def _make_mcp_with_tools(tmp_path):
    mcp = FastMCP("test")
    fetcher = MagicMock()
    index = MagicMock()
    register_docs(mcp, fetcher, index)
    return mcp, fetcher, index


def test_search_citrix_docs_calls_index(tmp_path):
    from citrix_mcp.models import SearchHit
    mcp, fetcher, index = _make_mcp_with_tools(tmp_path)
    index.search.return_value = [
        SearchHit(title="Test Page", url="https://docs.citrix.com/en-us/test.html", product="citrix-daas")
    ]
    # Get the registered tool function by name
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "search_citrix_docs")
    result = tool_fn(query="vda registration")
    index.search.assert_called_once_with("vda registration", product=None, host="docs.citrix.com", limit=10)
    assert len(result) == 1
    assert result[0]["title"] == "Test Page"


def test_fetch_citrix_doc_returns_clean_doc(tmp_path):
    mcp, fetcher, index = _make_mcp_with_tools(tmp_path)
    html = "<html><body><h1>Install Guide</h1><p>Content here.</p></body></html>"
    fetcher.fetch.return_value = {
        "url": "https://docs.citrix.com/en-us/citrix-daas/install.html",
        "html": html,
        "etag": None,
        "last_modified": None,
        "cached_at": "2025-01-01T00:00:00",
    }
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "fetch_citrix_doc")
    result = tool_fn(url="https://docs.citrix.com/en-us/citrix-daas/install.html")
    assert result["title"] == "Install Guide"
    assert "Content here" in result["markdown"]


def test_fetch_citrix_doc_returns_error_on_allowlist_violation(tmp_path):
    from citrix_mcp.fetcher import AllowlistError
    mcp, fetcher, index = _make_mcp_with_tools(tmp_path)
    fetcher.fetch.side_effect = AllowlistError("Host 'evil.com' not allowed")
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "fetch_citrix_doc")
    result = tool_fn(url="https://evil.com/inject")
    assert "error" in result


def test_list_citrix_products(tmp_path):
    from citrix_mcp.models import ProductInfo
    mcp, fetcher, index = _make_mcp_with_tools(tmp_path)
    index.list_products.return_value = [
        ProductInfo(product="citrix-daas", url_prefix="https://docs.citrix.com/en-us/citrix-daas/", page_count=42),
        ProductInfo(product="citrix-daas-sdk", url_prefix="https://developer-docs.citrix.com/en-us/citrix-daas-sdk/", page_count=10),
    ]
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "list_citrix_products")
    result = tool_fn()
    # Only docs.citrix.com products, not developer-docs.citrix.com
    assert len(result) == 1
    assert result[0]["product"] == "citrix-daas"
