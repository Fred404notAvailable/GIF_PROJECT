---
generated: true
name: "io.github.getsentry/sentry-mcp"
slug: "getsentry-sentry-mcp-2"
title: "Sentry"
version: "0.49.0"
approved_version: null
publisher: "io.github.getsentry"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 4
vetting_score: 75
repo: "https://github.com/getsentry/toolkit"
license: "MIT"
transport: "stdio"
---

# Sentry

> **MCP Server Catalog Entry**
> Publisher: `io.github.getsentry` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
MCP server for Sentry - error monitoring, issue tracking, and debugging for AI assistants

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: MIT in allowed list (+15); Pinning: exact version 0.49.0 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: resolve_issue, assign_issue); Secrets: requires SENTRY_AUTH_TOKEN, SENTRY_HOST, SENTRY_URL. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[dotnet-backend-patterns]]
- [[neon-postgres-branches]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
