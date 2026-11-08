---
generated: true
name: "io.github.modelcontextprotocol/memory"
slug: "modelcontextprotocol-memory-mcp-2"
title: "Memory"
version: "2.1.0"
approved_version: null
publisher: "Anthropic / Model Context Protocol"
publisher_verified: True
maintainer_class: "reference"
capability_class: "read-write"
requires_secrets: "No"
status: "selected"
module: General / Utilities
vetting_score: 75
repo: "https://github.com/modelcontextprotocol/servers"
license: "MIT"
transport: "stdio"
---

# Memory

> **MCP Server Catalog Entry**
> Publisher: `Anthropic / Model Context Protocol` (Verified: True) | Maintainer: `reference` | Status: **selected** | Vetting Score: **75/100**

## Description
Knowledge graph-based persistent memory system using entities, relations, and observations.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** No
- **Vetting Breakdown:** Publisher: reference (+25); Maintenance: not archived (+15); License: MIT in allowed list (+15); Pinning: exact version 2.1.0 (+15); Capability: read-write (tools: create_entities, create_relations, add_observations, delete_entities); Secrets: verified none required (+5). A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[autonomous-agent-patterns]]
- [[next-dev-loop]]
- [[secure-webapp]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
