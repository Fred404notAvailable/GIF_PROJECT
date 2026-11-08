---
generated: true
name: "io.prisma/mcp"
slug: "prisma-mcp-2"
title: "Prisma Postgres and Prisma Compute"
version: "1.1.0"
approved_version: null
publisher: "io.prisma"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 3
vetting_score: 75
repo: ""
license: "Apache-2.0"
transport: "streamable-http"
---

# Prisma Postgres and Prisma Compute

> **MCP Server Catalog Entry**
> Publisher: `io.prisma` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
Manage Prisma Postgres and existing Prisma Compute apps. Requires sign-in; does not upload code.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 1.1.0 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: manage_compute, execute_sql); Secrets: requires Authorization, Header: Authorization. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[neon-postgres-branches]]
- [[postgresql-table-design]]
- [[prisma-cli]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
