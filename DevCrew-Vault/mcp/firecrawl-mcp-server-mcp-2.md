---
generated: true
name: "io.github.firecrawl/firecrawl-mcp-server"
slug: "firecrawl-mcp-server-mcp-2"
title: "Firecrawl MCP Server"
version: "3.38.0"
approved_version: null
publisher: "io.github.firecrawl"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-only"
requires_secrets: "Yes"
status: "selected"
module: General / Utilities
vetting_score: 75
repo: "https://github.com/firecrawl/firecrawl-mcp-server.git"
license: "Apache-2.0"
transport: "stdio"
---

# Firecrawl MCP Server

> **MCP Server Catalog Entry**
> Publisher: `io.github.firecrawl` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
Firecrawl, the context API for AI agents: search, scrape, interact with the web, plus paper search.

## Safety & Capability Analysis
- **Capability Class:** `read-only`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 3.38.0 (+15); Remote: https vendor endpoint (+5); Capability: read-only (tools: scrape, crawl, map); Secrets: requires FIRECRAWL_API_KEY, Header: Authorization. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[autonomous-agent-patterns]]
- [[dotnet-backend-patterns]]
- [[next-dev-loop]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
