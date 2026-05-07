import pytest
from unittest.mock import MagicMock
from citrix_mcp.tools.daas_api import register_daas_api
from mcp.server.fastmcp import FastMCP


def _make_mcp_with_tools():
    mcp = FastMCP("test")
    fetcher = MagicMock()
    index = MagicMock()
    register_daas_api(mcp, fetcher, index)
    return mcp, fetcher, index


def test_search_daas_api_calls_index():
    from citrix_mcp.models import SearchHit
    mcp, fetcher, index = _make_mcp_with_tools()
    index.search.return_value = [
        SearchHit(title="Create Machine Catalog", url="https://developer-docs.citrix.com/en-us/citrix-daas/api/machinecatalogs.html")
    ]
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "search_daas_api")
    result = tool_fn(query="machine catalog")
    index.search.assert_called_once_with("machine catalog", host="developer-docs.citrix.com", limit=10)
    assert len(result) == 1


def test_get_daas_api_endpoint_by_url():
    mcp, fetcher, index = _make_mcp_with_tools()
    html = "<html><body><h1>Machine Catalogs API</h1><p>POST /machinecatalogs creates a catalog.</p></body></html>"
    fetcher.fetch.return_value = {
        "url": "https://developer-docs.citrix.com/en-us/citrix-daas/api/machinecatalogs.html",
        "html": html,
        "etag": None,
        "last_modified": None,
        "cached_at": "2025-01-01T00:00:00",
    }
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "get_daas_api_endpoint")
    result = tool_fn(endpoint_id_or_path="https://developer-docs.citrix.com/en-us/citrix-daas/api/machinecatalogs.html")
    assert result["title"] == "Machine Catalogs API"
    assert "machinecatalogs" in result["url"]


def test_get_daas_api_endpoint_by_name_no_results():
    mcp, fetcher, index = _make_mcp_with_tools()
    index.search.return_value = []
    tool_fn = next(t.fn for t in mcp._tool_manager.list_tools() if t.name == "get_daas_api_endpoint")
    result = tool_fn(endpoint_id_or_path="nonexistent endpoint xyz")
    assert "error" in result
