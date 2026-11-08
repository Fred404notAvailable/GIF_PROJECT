---
generated: true
name: "io.github.modelcontextprotocol/git"
slug: "modelcontextprotocol-git-mcp-2"
title: "Git"
version: "0.6.2"
approved_version: "0.6.2"
publisher: "Anthropic / Model Context Protocol"
publisher_verified: True
maintainer_class: "reference"
capability_class: "read-write"
requires_secrets: "No"
status: "approved"
module: General / Utilities
vetting_score: 75
repo: "https://github.com/modelcontextprotocol/servers"
license: "MIT"
transport: "stdio"
---

# Git

> **MCP Server Catalog Entry**
> Publisher: `Anthropic / Model Context Protocol` (Verified: True) | Maintainer: `reference` | Status: **approved** | Vetting Score: **75/100**

## Description
Read, search, diff, and commit to local Git repositories.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** No
- **Vetting Breakdown:** Publisher: reference (+25); Maintenance: not archived (+15); License: MIT in allowed list (+15); Pinning: exact version 0.6.2 (+15); Capability: read-write (tools: git_status, git_diff_unstaged, git_commit, git_add...); Secrets: verified none required (+5). A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
_None_

## Example Client Configuration
- [[configs/modelcontextprotocol-git-mcp-2.json]]
