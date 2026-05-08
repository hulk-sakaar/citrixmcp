import re
import logging
from urllib.parse import urlparse

import html2text
from bs4 import BeautifulSoup

from .models import CleanDoc

logger = logging.getLogger(__name__)

_STRIP_TAGS = ["nav", "header", "footer", "script", "style"]
_STRIP_CLASS_FRAGMENTS = [
    "feedback", "translation-banner", "mt-banner", "toc-sidebar",
    "breadcrumb", "language-switcher", "topbar", "navbar",
    "sticky-banner", "mt-feedback-banner",
    "content-left-wrapper",   # left sidebar nav on docs.citrix.com
    "sub-content-right-wrapper",  # right sidebar (TOC) on docs.citrix.com
]

# docs.citrix.com real page structure: article lives in div.sub-content-main
_ARTICLE_SELECTORS = [
    {"class": "sub-content-main"},   # docs.citrix.com article body
    {"class": "content-right-wrapper"},  # fallback
    "main",
    "article",
]

_DATE_RE = re.compile(
    r"\b([A-Z][a-z]+ \d{1,2},?\s+\d{4})\b"
)


def _make_converter() -> html2text.HTML2Text:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.ignore_images = True
    return h


def _strip_noise(soup: BeautifulSoup) -> None:
    for tag in _STRIP_TAGS:
        for el in soup.find_all(tag):
            el.decompose()
    for el in soup.find_all(role="navigation"):
        el.decompose()
    for el in soup.find_all(True):
        if el.attrs is None:
            continue
        classes = " ".join(el.get("class") or [])
        if any(frag in classes for frag in _STRIP_CLASS_FRAGMENTS):
            el.decompose()


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def _extract_meta(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Return (last_updated, contributed_by) from the page metadata area."""
    # docs.citrix.com: div.meta-data contains "September 6, 2025 Contributed by: X"
    meta_div = soup.find(class_="meta-data")
    if meta_div:
        text = meta_div.get_text(" ", strip=True)
        date_m = _DATE_RE.search(text)
        last_updated = date_m.group(1) if date_m else None
        contrib_m = re.search(r"Contributed\s+by[:\s]+(.+)", text, re.IGNORECASE)
        contributed_by = contrib_m.group(1).strip() if contrib_m else None
        # Skip single-character avatar abbreviations
        if contributed_by and len(contributed_by) <= 2:
            contributed_by = None
        return last_updated, contributed_by

    # Fallback: <time> tag
    time_el = soup.find("time")
    if time_el:
        return time_el.get_text(strip=True) or time_el.get("datetime"), None

    return None, None


def _get_body(soup: BeautifulSoup) -> str:
    for selector in _ARTICLE_SELECTORS:
        if isinstance(selector, dict):
            el = soup.find(**selector)
        else:
            el = soup.find(selector)
        if el:
            return str(el)
    return str(soup.find("body") or soup)


def clean(html: str, url: str) -> CleanDoc:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup)
    last_updated, contributed_by = _extract_meta(soup)
    _strip_noise(soup)
    body_html = _get_body(soup)
    markdown = _make_converter().handle(body_html)
    if not title:
        title = _fallback_title(url)
    return CleanDoc(
        title=title,
        url=url,
        markdown=markdown,
        last_updated=last_updated,
        contributed_by=contributed_by,
    )


def _fallback_title(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    if path:
        slug = path.split("/")[-1]
        slug = slug.rsplit(".", 1)[0] if "." in slug else slug
        return slug.replace("-", " ").replace("_", " ").title()
    return url
