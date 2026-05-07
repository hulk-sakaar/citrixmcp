from citrix_mcp.fetcher import AllowlistError, CitrixFetcher
from unittest.mock import patch
import pytest


def _make_fetcher(tmp_path):
    with patch("citrix_mcp.fetcher.httpx.Client"):
        return CitrixFetcher(cache_dir=tmp_path)


def test_allowed_docs_citrix(tmp_path):
    _make_fetcher(tmp_path)._validate_host("https://docs.citrix.com/en-us/citrix-daas/test.html")


def test_allowed_developer_cloud(tmp_path):
    _make_fetcher(tmp_path)._validate_host("https://developer.cloud.com/some/path")


def test_allowed_developer_docs(tmp_path):
    _make_fetcher(tmp_path)._validate_host("https://developer-docs.citrix.com/en-us/api.html")


def test_allowed_www_citrix(tmp_path):
    _make_fetcher(tmp_path)._validate_host("https://www.citrix.com/products/")


def test_rejected_example_com(tmp_path):
    with pytest.raises(AllowlistError):
        _make_fetcher(tmp_path)._validate_host("https://example.com/anything")


def test_rejected_subdomain(tmp_path):
    with pytest.raises(AllowlistError):
        _make_fetcher(tmp_path)._validate_host("https://evil.docs.citrix.com/inject")
