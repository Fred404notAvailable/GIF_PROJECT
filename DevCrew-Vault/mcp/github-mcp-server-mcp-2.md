---
generated: true
name: "io.github.github/github-mcp-server"
slug: "github-mcp-server-mcp-2"
title: "GitHub"
version: "2.1.0"
approved_version: null
publisher: "io.github.github"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 1
vetting_score: 75
repo: "https://github.com/github/github-mcp-server"
license: "MIT"
transport: "stdio"
---

# GitHub

> **MCP Server Catalog Entry**
> Publisher: `io.github.github` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
Connect AI assistants to GitHub - manage repos, issues, PRs, and workflows through natural language.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: MIT in allowed list (+15); Pinning: exact version 2.1.0 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: create_issue, create_pull_request, push_files, fork_repository); Secrets: requires Authorization, GITHUB_PERSONAL_ACCESS_TOKEN, Header: Authorization, TOKEN. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[devops-deploy]]
- [[infra-ci-cd-github-actions]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
