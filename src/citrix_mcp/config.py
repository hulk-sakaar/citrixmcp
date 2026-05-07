import os
from pathlib import Path

ALLOWED_HOSTS: frozenset[str] = frozenset({
    "docs.citrix.com",
    "developer.cloud.com",
    "developer-docs.citrix.com",
    "www.citrix.com",
})

_xdg = os.environ.get("XDG_CACHE_HOME")
CACHE_DIR: Path = (Path(_xdg) if _xdg else Path.home() / ".cache") / "citrix-mcp"

TTL_HOURS: int = int(os.environ.get("CITRIX_MCP_TTL_HOURS", "24"))

USER_AGENT: str = (
    "citrix-mcp/0.1 (+https://github.com/russellbell/citrix-mcp; "
    "contact: bell.russellc@gmail.com)"
)

MAX_CONCURRENCY: int = 4
