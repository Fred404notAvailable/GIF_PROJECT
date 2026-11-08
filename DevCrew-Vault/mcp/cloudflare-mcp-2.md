---
generated: true
name: "com.cloudflare.mcp/mcp"
slug: "cloudflare-mcp-2"
title: "com.cloudflare.mcp/mcp"
version: "1.0.0"
approved_version: null
publisher: "com.cloudflare.mcp"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 1
vetting_score: 75
repo: "https://github.com/cloudflare/mcp-server-cloudflare"
license: "Apache-2.0"
transport: "streamable-http"
---

# com.cloudflare.mcp/mcp

> **MCP Server Catalog Entry**
> Publisher: `com.cloudflare.mcp` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
Cloudflare MCP servers

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 1.0.0 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: deploy_worker, kv_set, d1_execute); Secrets: requires CLOUDFLARE_API_TOKEN, Header: Authentication. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[cloudflare]]
- [[frameworks-on-cloudflare]]
- [[hono]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
