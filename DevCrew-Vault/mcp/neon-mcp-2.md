---
generated: true
name: "com.neon/mcp"
slug: "neon-mcp-2"
title: "Neon"
version: "2.0.0"
approved_version: null
publisher: "com.neon"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 3
vetting_score: 75
repo: "https://github.com/neondatabase/mcp-server-neon"
license: "Apache-2.0"
transport: "streamable-http"
---

# Neon

> **MCP Server Catalog Entry**
> Publisher: `com.neon` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
Official Neon MCP server for managing Neon projects and Lakebase Postgres databases.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 2.0.0 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: create_branch, create_project, execute_sql); Secrets: requires Header: Authorization, NEON_API_KEY. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[neon-postgres-branches]]
- [[supabase]]
- [[neon-postgres]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
