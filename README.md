# citrix-mcp

An MCP server for Citrix documentation, DaaS API reference, and community content.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)

## Install

```bash
uv sync
```

After installing dependencies, install the Playwright browser (required for community.citrix.com which uses Cloudflare protection):

```bash
uv run playwright install chromium
```

## Index build

Build the documentation search index (one-time setup, takes a few minutes):

```bash
uv run citrix-mcp --refresh-index
```

This crawls the sitemaps for `docs.citrix.com` and `developer-docs.citrix.com` and builds a local FTS5 search index.

## Setup

### Kiro / Claude Desktop

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "citrix-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/citrix_mcp", "run", "citrix-mcp"]
    }
  }
}
```

To also rebuild the index on each server start (useful for keeping docs fresh):

```json
{
  "mcpServers": {
    "citrix-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/citrix_mcp", "run", "citrix-mcp", "--refresh-index"]
    }
  }
}
```

### CLI

```bash
uv run citrix-mcp
```

## Available tools

| Tool | Description |
|------|-------------|
| `search_citrix_docs` | Search Citrix product documentation (docs.citrix.com). Filter by product slug. |
| `fetch_citrix_doc` | Fetch a docs.citrix.com page as clean Markdown. |
| `list_citrix_products` | List all product areas in the documentation index. |
| `search_daas_api` | Search the Citrix DaaS REST API reference. |
| `get_daas_api_endpoint` | Fetch a DaaS API reference page by URL or name. |
| `search_community` | Search the Citrix Community across all content types (forums, tech zone, blogs). |
| `fetch_url` | Fetch any allowlisted Citrix URL as clean Markdown. |

### Allowed hosts

The server can fetch content from these domains:

- `docs.citrix.com`
- `developer-docs.citrix.com`
- `developer.cloud.com`
- `www.citrix.com`
- `community.citrix.com` (uses headless browser via Playwright)

## Cache

Fetched pages are cached locally at `~/.cache/citrix-mcp/pages/` with a default TTL of 24 hours. Override with:

```bash
export CITRIX_MCP_TTL_HOURS=12
```

Clear the cache manually:

```bash
uv run citrix-mcp --clear-cache
```

## Tests

```bash
uv run pytest -q
```

## Out of scope for v1

- PowerShell SDK integration
- OData queries
- Docker/containerization
