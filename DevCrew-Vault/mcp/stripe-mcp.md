---
generated: true
name: "com.stripe/mcp"
slug: "stripe-mcp"
title: "com.stripe/mcp"
version: "0.2.4"
approved_version: null
publisher: "com.stripe"
publisher_verified: True
maintainer_class: "official-vendor"
capability_class: "read-write"
requires_secrets: "Yes"
status: "selected"
module: 1
vetting_score: 75
repo: "https://github.com/stripe/agent-toolkit"
license: "Apache-2.0"
transport: "streamable-http"
---

# com.stripe/mcp

> **MCP Server Catalog Entry**
> Publisher: `com.stripe` (Verified: True) | Maintainer: `official-vendor` | Status: **selected** | Vetting Score: **75/100**

## Description
MCP server integrating with Stripe - tools for customers, products, payments, and more.

## Safety & Capability Analysis
- **Capability Class:** `read-write`
- **Secrets Required:** Yes
- **Vetting Breakdown:** Publisher: official-vendor (+25); Maintenance: not archived (+15); License: Apache-2.0 in allowed list (+15); Pinning: exact version 0.2.4 (+15); Remote: https vendor endpoint (+5); Capability: read-write (tools: create_customer, create_payment_intent, create_invoice); Secrets: requires STRIPE_SECRET_KEY. A clean scan does not prove a server is safe.

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
- [[stripe-best-practices]]

## Example Client Configuration
_Awaiting human approval in `catalog.yaml`_
