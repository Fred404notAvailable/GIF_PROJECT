---
generated: true
name: "io.github.ClickHouse/mcp-clickhouse"
slug: "clickhouse-mcp-2"
title: "ClickHouse"
version: "0.7.0"
approved_version: null
publisher: "io.github.ClickHouse"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 3
vetting_score: 70
repo: "https://github.com/ClickHouse/mcp-clickhouse"
license: "Apache-2.0"
transport: "stdio"
---

# ClickHouse

> **MCP Server Catalog Entry**
> Publisher: `io.github.ClickHouse` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **70/100**

## Description
Official ClickHouse MCP server for querying and exploring ClickHouse clusters and chDB.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 0.7.0 (+15); Capability: read-write (tools: execute_query); Secrets: requires CLICKHOUSE_ALLOW_DROP, CLICKHOUSE_ALLOW_WRITE_ACCESS, CLICKHOUSE_CA_CERT, CLICKHOUSE_CLIENT_CERT, CLICKHOUSE_CLIENT_CERT_KEY, CLICKHOUSE_DATABASE, CLICKHOUSE_HOST, CLICKHOUSE_MCP_MAX_WORKERS, CLICKHOUSE_MCP_QUERY_TIMEOUT, CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT, CLICKHOUSE_ROLE, CLICKHOUSE_SECURE, CLICKHOUSE_TLS_MODE, CLICKHOUSE_USER, CLICKHOUSE_VERIFY. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[supabase]]
- [[clickhouse-best-practices]]
- [[neon-postgres-branches]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
