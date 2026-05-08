import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock
from citrix_mcp.sitemap_index import SitemapIndex

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _make_index(tmp_path: Path) -> SitemapIndex:
    return SitemapIndex(db_dir=tmp_path)


def _xml_response(path: Path) -> MagicMock:
    r = MagicMock()
    r.text = path.read_text()
    r.raise_for_status = MagicMock()
    return r


def test_search_empty_index_returns_empty(tmp_path):
    idx = _make_index(tmp_path)
    results = idx.search("citrix daas vda")
    assert results == []


def test_list_products_empty_index_returns_empty(tmp_path):
    idx = _make_index(tmp_path)
    assert idx.list_products() == []


def test_refresh_indexes_pages(tmp_path):
    index_xml = FIXTURE_DIR / "sitemap_index_sample.xml"
    product_xml = FIXTURE_DIR / "sitemap_product_sample.xml"

    call_count = [0]
    def fake_get(url, **kwargs):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        # First call = index, subsequent calls = product sitemap
        if call_count[0] == 0:
            r.text = index_xml.read_text()
        else:
            r.text = product_xml.read_text()
        call_count[0] += 1
        return r

    with patch("citrix_mcp.sitemap_index.httpx.get", side_effect=fake_get):
        idx = _make_index(tmp_path)
        # Only refresh one root to keep test predictable
        from citrix_mcp.sitemap_index import _SITEMAP_ROOTS
        original_roots = _SITEMAP_ROOTS.copy() if hasattr(_SITEMAP_ROOTS, 'copy') else list(_SITEMAP_ROOTS)

        import citrix_mcp.sitemap_index as si_module
        si_module._SITEMAP_ROOTS = ["https://docs.citrix.com/sitemap.xml"]
        try:
            total = idx.refresh()
        finally:
            si_module._SITEMAP_ROOTS = original_roots

    # Two product sitemaps in the index xml, each mock returns 2 URLs → 4 total
    assert total == 4


def test_search_after_refresh(tmp_path):
    index_xml = FIXTURE_DIR / "sitemap_index_sample.xml"
    product_xml = FIXTURE_DIR / "sitemap_product_sample.xml"

    call_count = [0]
    def fake_get(url, **kwargs):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        if call_count[0] == 0:
            r.text = index_xml.read_text()
        else:
            r.text = product_xml.read_text()
        call_count[0] += 1
        return r

    import citrix_mcp.sitemap_index as si_module
    original_roots = list(si_module._SITEMAP_ROOTS)
    si_module._SITEMAP_ROOTS = ["https://docs.citrix.com/sitemap.xml"]
    try:
        with patch("citrix_mcp.sitemap_index.httpx.get", side_effect=fake_get):
            idx = _make_index(tmp_path)
            idx.refresh()
        results = idx.search("vda")
    finally:
        si_module._SITEMAP_ROOTS = original_roots

    assert len(results) >= 1
    assert any("vda" in r.url.lower() for r in results)


def test_refresh_follows_urlset_sitemaps(tmp_path):
    """Root sitemap uses <urlset> with <url><loc>...sitemap.xml entries — must recurse."""
    root_xml = FIXTURE_DIR / "sitemap_urlset_of_sitemaps.xml"
    product_xml = FIXTURE_DIR / "sitemap_product_sample.xml"

    def fake_get(url, **kwargs):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        if "en-us" not in url:
            r.text = root_xml.read_text()
        else:
            r.text = product_xml.read_text()
        return r

    import citrix_mcp.sitemap_index as si_module
    original_roots = list(si_module._SITEMAP_ROOTS)
    si_module._SITEMAP_ROOTS = ["https://docs.citrix.com/sitemap.xml"]
    try:
        with patch("citrix_mcp.sitemap_index.httpx.get", side_effect=fake_get):
            idx = _make_index(tmp_path)
            total = idx.refresh()
        # 2 sub-sitemaps × 2 content pages each = 4 real pages
        assert total == 4
        # No .xml URLs should appear in the index
        results = idx.search("sitemap")
        assert results == []
        # Real content is searchable
        vda_results = idx.search("vda")
        assert len(vda_results) >= 1
    finally:
        si_module._SITEMAP_ROOTS = original_roots


def test_slug_title_strips_extension(tmp_path):
    from citrix_mcp.sitemap_index import _slug_title
    assert _slug_title("https://docs.citrix.com/en-us/citrix-daas/disaster-recovery.html") == "Disaster Recovery"
    assert _slug_title("https://docs.citrix.com/en-us/citrix-daas/sitemap.xml") == "Sitemap"


def test_refresh_is_idempotent(tmp_path):
    """Calling refresh twice should not duplicate entries."""
    index_xml = FIXTURE_DIR / "sitemap_index_sample.xml"
    product_xml = FIXTURE_DIR / "sitemap_product_sample.xml"

    def fake_get(url, **kwargs):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        # Use URL to decide which XML to return
        if "sitemap.xml" == url.split("/")[-1] and "en-us" not in url:
            r.text = index_xml.read_text()
        else:
            r.text = product_xml.read_text()
        return r

    import citrix_mcp.sitemap_index as si_module
    original_roots = list(si_module._SITEMAP_ROOTS)
    si_module._SITEMAP_ROOTS = ["https://docs.citrix.com/sitemap.xml"]
    try:
        with patch("citrix_mcp.sitemap_index.httpx.get", side_effect=fake_get):
            idx = _make_index(tmp_path)
            total1 = idx.refresh()
            total2 = idx.refresh()
    finally:
        si_module._SITEMAP_ROOTS = original_roots

    # Count should be consistent, not doubled
    assert total1 == total2
