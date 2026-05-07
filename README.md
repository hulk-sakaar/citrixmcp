# citrix-mcp

An MCP server for Citrix documentation and DaaS API integration.

## Install

```bash
uv sync
```

## Index build

Build the documentation index once:

```bash
uv run citrix-mcp --refresh-index
```

## Claude Desktop setup

Add to `claude_desktop_config.json`:

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

## Claude Code setup

```bash
uv run citrix-mcp
```

## Tests

```bash
uv run pytest -q
```

## Available tools

- `search_docs` — Search Citrix documentation
- `fetch_docs` — Fetch full documentation page
- `query_daas_api` — Query DaaS API for resource information
- `list_daas_resources` — List available DaaS resources
- `get_resource_details` — Get details for a specific resource
- `search_combined` — Search both docs and DaaS API
- `validate_configuration` — Validate Citrix configuration
- `monitor_health` — Monitor resource health status

## Out of scope for v1

- PowerShell SDK integration
- OData queries
- Docker/containerization
