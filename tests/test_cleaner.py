from pathlib import Path
from citrix_mcp.cleaner import clean

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "docs_citrix_com_sample.html"


def test_title_extracted():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert doc.title == "Test Article"


def test_article_body_present():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "article body content" in doc.markdown


def test_code_block_preserved():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "Get-BrokerMachine" in doc.markdown


def test_nav_stripped():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "Main Navigation" not in doc.markdown


def test_footer_stripped():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "Footer Content" not in doc.markdown


def test_feedback_stripped():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "Send us your feedback" not in doc.markdown


def test_translation_banner_stripped():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert "machine translated" not in doc.markdown


def test_date_extracted():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert doc.last_updated == "January 15, 2025"


def test_contributed_by_extracted():
    html = FIXTURE_PATH.read_text()
    doc = clean(html, "https://docs.citrix.com/en-us/test/page.html")
    assert doc.contributed_by is not None
    assert "Citrix Documentation Team" in doc.contributed_by


def test_fallback_title_from_url():
    doc = clean("<html><body><p>No heading.</p></body></html>", "https://docs.citrix.com/en-us/citrix-daas/vda-registration.html")
    assert doc.title == "Vda Registration"
