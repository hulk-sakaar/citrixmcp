import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from citrix_mcp.fetcher import CitrixFetcher, AllowlistError


def _mock_response(html: str, url: str = "https://docs.citrix.com/en-us/test.html", status: int = 200):
    r = MagicMock()
    r.status_code = status
    r.text = html
    r.headers = {}
    r.url = url
    r.raise_for_status = MagicMock()
    return r


def test_fetch_raises_for_disallowed_url(tmp_path):
    with patch("citrix_mcp.fetcher.httpx.Client"):
        fetcher = CitrixFetcher(cache_dir=tmp_path)
    with pytest.raises(AllowlistError):
        fetcher.fetch("https://example.com/bad")


def test_fetch_writes_cache_on_200(tmp_path):
    html = "<html><body><h1>Hello</h1></body></html>"
    url = "https://docs.citrix.com/en-us/test.html"
    mock_resp = _mock_response(html, url)

    with patch("citrix_mcp.fetcher.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.get.return_value = mock_resp
        fetcher = CitrixFetcher(cache_dir=tmp_path)
        result = fetcher.fetch(url)

    assert result["html"] == html
    assert result["url"] == url
    pages_dir = tmp_path / "pages"
    assert any(pages_dir.iterdir())


def test_fetch_uses_cache_on_second_call(tmp_path):
    html = "<html><body><p>Cached.</p></body></html>"
    url = "https://docs.citrix.com/en-us/cached.html"
    mock_resp = _mock_response(html, url)

    with patch("citrix_mcp.fetcher.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.get.return_value = mock_resp
        fetcher = CitrixFetcher(cache_dir=tmp_path, ttl_hours=24)
        fetcher.fetch(url)
        fetcher.fetch(url)

    assert mock_client.get.call_count == 1  # second call hits cache


def test_fetch_sends_conditional_headers_on_stale_cache(tmp_path):
    html = "<html><body><p>Content.</p></body></html>"
    url = "https://docs.citrix.com/en-us/stale.html"
    etag = '"abc123"'

    # Prime cache with expired entry
    import hashlib
    from datetime import datetime, timedelta
    cache_key = hashlib.sha256(url.encode()).hexdigest()
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir(parents=True)
    stale_entry = {
        "url": url,
        "html": html,
        "etag": etag,
        "last_modified": None,
        "cached_at": (datetime.now() - timedelta(hours=48)).isoformat(),
    }
    (pages_dir / f"{cache_key}.json").write_text(json.dumps(stale_entry))

    mock_resp = _mock_response(html, url)
    mock_resp.headers = {"ETag": etag}

    with patch("citrix_mcp.fetcher.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.get.return_value = mock_resp
        fetcher = CitrixFetcher(cache_dir=tmp_path, ttl_hours=24)
        fetcher.fetch(url)

    sent_headers = mock_client.get.call_args.kwargs.get("headers", {})
    assert "If-None-Match" in sent_headers


def test_clear_cache_removes_files(tmp_path):
    html = "<html><body><p>To clear.</p></body></html>"
    url = "https://docs.citrix.com/en-us/clear.html"
    mock_resp = _mock_response(html, url)

    with patch("citrix_mcp.fetcher.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.get.return_value = mock_resp
        fetcher = CitrixFetcher(cache_dir=tmp_path)
        fetcher.fetch(url)

    pages_dir = tmp_path / "pages"
    assert any(pages_dir.iterdir())
    fetcher.clear_cache()
    assert not any(pages_dir.iterdir())
