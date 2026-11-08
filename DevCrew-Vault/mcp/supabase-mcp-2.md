---
generated: true
name: "com.supabase/mcp"
slug: "supabase-mcp-2"
title: "Supabase"
version: "0.16.1"
approved_version: null
publisher: "com.supabase"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 3
vetting_score: 75
repo: "https://github.com/supabase/mcp"
license: "MIT"
transport: "stdio"
---

# Supabase

> **MCP Server Catalog Entry**
> Publisher: `com.supabase` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
MCP server for interacting with the Supabase platform

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: MIT in allowed list (+15); Pinning: exact version 0.16.1 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: execute_sql, manage_branch); Secrets: requires SUPABASE_ACCESS_TOKEN. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[neon-postgres-branches]]
- [[supabase]]
- [[supabase-postgres-best-practices]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
