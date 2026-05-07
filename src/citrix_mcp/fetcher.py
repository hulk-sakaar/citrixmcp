import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import ALLOWED_HOSTS, CACHE_DIR, MAX_CONCURRENCY, TTL_HOURS, USER_AGENT

logger = logging.getLogger(__name__)

_semaphore = threading.Semaphore(MAX_CONCURRENCY)
_PAGES_SUBDIR = "pages"


class AllowlistError(ValueError):
    pass


def _hostname(url: str) -> str:
    return urlparse(url).hostname or ""


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class CitrixFetcher:
    def __init__(self, cache_dir: Path | None = None, ttl_hours: int | None = None):
        self._cache_dir = (cache_dir or CACHE_DIR) / _PAGES_SUBDIR
        self._ttl = timedelta(hours=ttl_hours if ttl_hours is not None else TTL_HOURS)
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        )

    def _validate_host(self, url: str) -> None:
        host = _hostname(url)
        if host not in ALLOWED_HOSTS:
            raise AllowlistError(
                f"Host {host!r} is not in the allowlist. Allowed: {sorted(ALLOWED_HOSTS)}"
            )

    def fetch(self, url: str) -> dict:
        """Fetch url, returning dict with keys: url, html, etag, last_modified, cached_at."""
        self._validate_host(url)

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / f"{_cache_key(url)}.json"

        cached: dict | None = None
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(cached["cached_at"])
            if datetime.now() - cached_at < self._ttl:
                logger.debug("Cache hit (fresh): %s", url)
                return cached

        headers: dict[str, str] = {}
        if cached:
            if cached.get("etag"):
                headers["If-None-Match"] = cached["etag"]
            elif cached.get("last_modified"):
                headers["If-Modified-Since"] = cached["last_modified"]

        with _semaphore:
            time.sleep(0.1)  # polite per-request spacing
            logger.info("Fetching: %s", url)
            response = self._client.get(url, headers=headers)

        # Re-validate after redirect — final URL host must be allowed
        final_url = str(response.url)
        self._validate_host(final_url)

        if response.status_code == 304 and cached:
            logger.debug("304 Not Modified, refreshing cached_at: %s", url)
            cached["cached_at"] = datetime.now().isoformat()
            cache_file.write_text(json.dumps(cached))
            return cached

        response.raise_for_status()

        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")

        result = {
            "url": final_url,
            "html": response.text,
            "etag": etag,
            "last_modified": last_modified,
            "cached_at": datetime.now().isoformat(),
        }
        cache_file.write_text(json.dumps(result))
        return result

    def clear_cache(self) -> None:
        if self._cache_dir.exists():
            for f in self._cache_dir.iterdir():
                if f.is_file():
                    f.unlink()
        logger.info("Cache cleared: %s", self._cache_dir)
