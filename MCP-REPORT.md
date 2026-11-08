# DevCrew MCP Server Catalog Report (Ingest, Vet, Index, Map)

> [!IMPORTANT]
> **Safety Assurance:** No MCP server code was installed, executed, or run at any point during this build. No tokens, secrets, or credentials have been collected or stored. All generated client configuration files are strictly examples containing environment variable placeholders (`${VAR}`). Nothing becomes `approved` without an explicit human decision recorded in `catalog.yaml`.

---

## 1. Executive Summary

The MCP catalog has been updated to use **threshold-driven selection** over the full ingested registry candidates rather than quota-driven padding. Only servers meeting strict developer-tool fit, minimum vetting floor (score >= 50, verified namespace or official/reference class, allowed license, pinned semver), and genuine module relevance are selected. Ceilings are respected and module shortfalls are honestly reported.

| Metric | Skills Layer | MCP Catalog Layer | Total Knowledge Graph |
|---|:---:|:---:|:---:|
| **Registry Universe** | 4,000+ raw packages | 58,646 registry records across 587 pages | 62,000+ cataloged records |
| **Ingested Candidates** | 99 selected skills | 59534 servers | 59633 processed entities |
| **Vetted & Selected** | 99 skills (1 unfilled) | 16 module + 8 utilities (24 total) | 123 core assets |
| **Approved by Human** | 99 skills | 0 (awaiting human decision in `catalog.yaml`) | 99 approved assets |
| **Typed Relationships** | 380 complements, 137 alternates | 51 `pairs-with` links | 568 typed edges |
| **Link Integrity** | 0 dangling links | 0 dangling links | 100% link consistency |

---

## 2. Full Candidate Ingestion & Vetting Funnel

Candidate ingestion evaluated servers across the multi-stage vetting funnel:

| Funnel Stage | Server Count | Percentage of Ingested | Gate Description |
|---|:---:|:---:|---|
| **1. Total Ingested Candidates** | **59534** | 100.0% | Registry latest packages, multi-lookup vendor seeds, and reference servers |
| **2. Passed Developer-Tool Fit** | **50933** | 85.6% | Excluded trading, real estate, lead generation, salons, and consumer tools |
| **3. Passed Vetting Floor** | **26** | 0.0% | Score >= 50, allowed license (MIT/Apache/BSD/CC-BY), pinned semver, credible namespace |
| **4. Passed Module / Utility Relevance** | **24** | 0.0% | Strong-signal domain match or >= 2 non-generic module keywords |
| **5. Selected for Vault Catalog** | **24** | 0.0% | 16 module servers (under 7 ceilings) + 8 foundational utilities |

---

## 3. Seed Multi-Lookup Results Summary

Multi-lookup queries (name, publisher namespace, repository URL) resolved major vendor presences in the registry (see `MCP-SEED-RESULTS.md` for full query logs):
- **Found in Registry (18):** GitHub (`io.github.github/github-mcp-server`), Playwright (`io.github.microsoft/playwright-mcp`), Supabase (`com.supabase/mcp`), Sentry (`io.github.getsentry/sentry-mcp`), Prisma (`io.prisma/mcp`), Browserbase (`io.github.browserbase/mcp-server-browserbase`), Stripe (`com.stripe/mcp`), Cloudflare (`com.cloudflare.mcp/mcp`), Neon (`com.neon/mcp`), ClickHouse (`io.github.ClickHouse/mcp-clickhouse`), Firebase (`io.github.firebase/firebase-mcp`), Figma (`com.figma.mcp/mcp`), Context7 (`io.github.upstash/context7`), Axiom (`co.axiom/mcp`), Comet Opik (`io.github.comet-ml/opik-mcp`), Exa (`ai.exa/exa`), Firecrawl (`io.github.firecrawl/firecrawl-mcp-server`), AWS OSCAL (`io.github.awslabs/mcp-server-for-oscal`).
- **Community / Ambiguous (2):** Kubernetes (`io.github.containers/kubernetes-mcp-server` under `containers` org), E2B (`com.mcparmory/e2b` community wrapper).
- **Not in Registry (2):** Docker (official `docker/mcp-server` not published), general AWS (`awslabs/mcp-server-aws` not published; only OSCAL server published).

---

## 4. Module Ceilings, Selections & Shortfalls

Module targets represent **ceilings, not quotas**. General utilities are placed outside the 7 modules without synthetic padding. Shortfalls are preserved and reported directly.

| Module ID | Module Name | Ceiling | Selected | Shortfall | Selected Servers |
|:---:|---|:---:|:---:|:---:|---|
| **1** | Modern Backend & API Development | 7 | 3 | -4 | **3/7** (`cloudflare-mcp-2`, `stripe-mcp`, `github-mcp-server-mcp-2`) |
| **2** | Frontend & UI Engine Frameworks | 7 | 1 | -6 | **1/7** (`figma-mcp-2`) |
| **3** | Database, Vector & Storage Management | 7 | 5 | -2 | **5/7** (`neon-mcp-2`, `supabase-mcp-2`, `prisma-mcp-2`, `clickhouse-mcp-2`, `firebase-mcp-2`) |
| **4** | Security, Auditing & SecOps | 7 | 2 | -5 | **2/7** (`getsentry-sentry-mcp-2`, `awslabs-server-for-oscal-mcp-2`) |
| **5** | AI Architecture, LLM & Prompt Engineering | 7 | 3 | -4 | **3/7** (`exa-mcp-2`, `axiom-mcp-2`, `comet-ml-opik-mcp-2`) |
| **6** | Testing, QA & Reliability Engineering | 7 | 2 | -5 | **2/7** (`microsoft-playwright-mcp-2`, `server-browserbase-mcp-2`) |
| **7** | DevOps, Containers & Cloud Automation | 7 | 0 | -7 | **0/7** (_None (shortfall)_) |

**Total Module Servers Selected:** 16/49 (Total Module Shortfall: 33).
**General / Utilities Selected:** 8 servers (`filesystem`, `git`, `fetch`, `time`, `memory`, `sequential-thinking`, `context7`).
**Combined Catalog Total:** 24 verified MCP servers.

---

## 5. Dropped Servers and Exclusions

Under the strict vetting floor and user license restrictions, the following servers are excluded from selected status:

| Excluded / Dropped Server | Previous Status | Reason for Exclusion / Placement as Candidate |
|---|---|---|
| `io.github.modelcontextprotocol/everything` | Selected (old) | Reference test harness server containing mock echo/sampler tools. Demoted to candidate per Problem 5. |
| `io.github.hashicorp/terraform-mcp-server` | Selected (old) | Licensed under MPL-2.0. Excluded from selected pending explicit user decision in `DECISIONS-NEEDED.md`. |
| `com.mcparmory/e2b` | Candidate | Failed module relevance: requires >=2 distinct non-generic keywords or 1 strong-signal keyword |
| `io.github.modelcontextprotocol/everything` | Candidate | Protocol test server, excluded from selected per Round 3 Item 3 |
| `com.microsoft/playwright-cloud-browsers` | Candidate | Failed vetting floor: unverified namespace and community maintainer class |
| `ac.tandem/docs-mcp` | Candidate | Failed vetting floor: license: unknown |
| `ae.beachclubs/mcp` | Candidate | Failed developer-tool fit: contains 'beachclub' (non-developer purpose) |
| `ae.waggle/fenlight` | Candidate | Failed developer-tool fit: contains 'shopping' (non-developer purpose) |
| `ae.waggle/vera` | Candidate | Failed vetting floor: license: unknown |
| `aero.events/events` | Candidate | Failed vetting floor: license: unknown |
| `agency.ottobot/licensed-house-painters` | Candidate | Failed vetting floor: license: unknown |
| `agency.thebureauoflostcontext/bureau-public` | Candidate | Failed vetting floor: license: unknown |

---

## 6. Skill-to-Server Pairing Quality

Pairing requires **at least 2 shared tech tags** OR **1 tag from the strong-signal list** (e.g. Stripe, Supabase, Playwright, Figma, Cloudflare, Sentry). Servers with no genuine affinity have 0 pairs (no synthetic padding).

### Pairing Distribution Across Selected Servers
- **Servers with 0 pairs:** 4 (foundational utilities e.g. `filesystem`, `time`, `sequential-thinking` without synthetic links)
- **Servers with 1 pair:** 2
- **Servers with 2 pairs:** 5
- **Servers with 3 pairs:** 13
- **Total `pairs-with` Links Generated:** 51 links.

---

## 7. Open Human Decisions

1. **Review Pending Approvals in `MCP-APPROVALS-NEEDED.md`:** Decide which vetted servers to approve for client generation.
2. **Filesystem Scoping:** Confirm workspace directory path (`args: ["d:\UPS_project"]`) before running filesystem tools.
3. **MPL-2.0 Decision:** Decide whether to allow MPL-2.0 in `devcrew.config.yaml` to unlock Terraform skills and MCP servers.