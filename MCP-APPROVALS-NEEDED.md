# MCP Server Approvals Needed

> [!IMPORTANT]
> MCP servers execute running code and access live external credentials.
> Therefore, the agent **never auto-approves** an MCP server.
> Every server below has been vetted by static analysis, verified against the registry snapshot, and recommended by the catalog.
> To approve a server, copy its exact version pin into `DevCrew-Vault/catalog.yaml` under `approvals:`.

**Generated:** 2026-11-08 18:36:38 UTC
**Selected Module Servers Awaiting Approval:** 15
**General / Utility Servers Awaiting Approval:** 5
**Already Approved Servers:** 4

## Critical Operational & Combination Risk Notes

> [!CAUTION]
> Review these operational combination risks before granting human approval in `catalog.yaml`:

1. **Combination Risk: `git` + `filesystem`:**
   When both `io.github.modelcontextprotocol/filesystem` and `io.github.modelcontextprotocol/git` are enabled simultaneously,
   an agent possesses full capability to modify local source files, stage changes, and commit or push to remote repositories.
   **Mitigation:** Enforce human confirmation gates on commit/push tools and restrict filesystem scope to the target project directory.

2. **Combination Risk: `fetch` + Write-Capable Servers:**
   The `fetch` server retrieves external web pages. Untrusted external HTML/Markdown can contain indirect prompt-injection attempts
   (`ignore prior instructions`, exfiltration triggers). If enabled alongside write-capable servers (e.g. database, cloud, git, filesystem),
   an injected prompt could trigger unintended state changes, automated writes, or API calls.
   **Mitigation:** Sanitize fetched web content and mandate human confirmation before write tools are triggered from fetched workflows.

3. **`filesystem` Directory Scoping:**
   The filesystem server operates with `read-write` capabilities. It must be strictly bounded to the workspace directory only
   (e.g. `args: ["d:\UPS_project"]`) to prevent arbitrary directory traversal.

4. **Financial & Destructive Mutating Tools:**
   Servers marked `read-write` (Stripe, Cloudflare, Neon, ClickHouse, Firebase, Supabase) can mutate cloud infrastructure or initiate transactions.
   Ensure client configuration environment variable values use restricted, scoped API tokens.

## Verified General / Utility Servers
Cross-cutting foundational tools serving all modules (no quota target):

| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `io.github.firecrawl/firecrawl-mcp-server` | `3.38.0` | `Apache-2.0` (registry-record) | `io.github.firecrawl` | Yes | `official-vendor` | `stdio` | `npm` | `read-only` | FIRECRAWL_API_KEY, Header: Authorization | 75/100 |
| `io.github.modelcontextprotocol/fetch` | `0.6.2` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `pypi` | `read-only` | None | 75/100 |
| `io.github.modelcontextprotocol/filesystem` | `2.2.0` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `npm` | `read-write` | None | 75/100 |
| `io.github.modelcontextprotocol/git` | `0.6.2` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `pypi` | `read-write` | None | 75/100 |
| `io.github.modelcontextprotocol/memory` | `2.1.0` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `npm` | `read-write` | None | 75/100 |
| `io.github.modelcontextprotocol/sequential-thinking` | `2.1.1` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `npm` | `read-only` | None | 75/100 |
| `io.github.modelcontextprotocol/time` | `0.6.2` | `MIT` (registry-record) | `Anthropic / Model Context Protocol` | Yes | `reference` | `stdio` | `pypi` | `read-only` | None | 75/100 |
| `io.github.upstash/context7` | `4.5.1` | `Apache-2.0` (registry-record) | `io.github.upstash` | Yes | `official-vendor` | `stdio` | `npm,mcpb` | `read-only` | CONTEXT7_API_KEY, Header: Authorization | 75/100 |

## Verified Selected Servers by Module

### Module 1: Modern Backend & API Development
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `com.cloudflare.mcp/mcp` | `1.0.0` | `Apache-2.0` (registry-record) | `com.cloudflare.mcp` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | CLOUDFLARE_API_TOKEN, Header: Authentication | 75/100 |
| `com.stripe/mcp` | `0.2.4` | `Apache-2.0` (registry-record) | `com.stripe` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | STRIPE_SECRET_KEY | 75/100 |
| `io.github.github/github-mcp-server` | `2.1.0` | `MIT` (registry-record) | `io.github.github` | Yes | `official-vendor` | `stdio` | `oci` | `read-write` | Authorization, GITHUB_PERSONAL_ACCESS_TOKEN, Header: Authorization, TOKEN | 75/100 |

### Module 2: Frontend & UI Engine Frameworks
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `com.figma.mcp/mcp` | `1.0.3` | `MIT` (registry-record) | `com.figma.mcp` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | FIGMA_ACCESS_TOKEN | 75/100 |

### Module 3: Database, Vector & Storage Management
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `com.neon/mcp` | `2.0.0` | `Apache-2.0` (registry-record) | `com.neon` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | Header: Authorization, NEON_API_KEY | 75/100 |
| `com.supabase/mcp` | `0.16.1` | `MIT` (registry-record) | `com.supabase` | Yes | `official-vendor` | `stdio` | `npm` | `read-write` | SUPABASE_ACCESS_TOKEN | 75/100 |
| `io.prisma/mcp` | `1.1.0` | `Apache-2.0` (registry-record) | `io.prisma` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | Authorization, Header: Authorization | 75/100 |
| `io.github.ClickHouse/mcp-clickhouse` | `0.7.0` | `Apache-2.0` (registry-record) | `io.github.ClickHouse` | Yes | `official-vendor` | `stdio` | `pypi,oci` | `read-write` | CLICKHOUSE_ALLOW_DROP, CLICKHOUSE_ALLOW_WRITE_ACCESS, CLICKHOUSE_CA_CERT, CLICKHOUSE_CLIENT_CERT, CLICKHOUSE_CLIENT_CERT_KEY, CLICKHOUSE_DATABASE, CLICKHOUSE_HOST, CLICKHOUSE_MCP_MAX_WORKERS, CLICKHOUSE_MCP_QUERY_TIMEOUT, CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT, CLICKHOUSE_ROLE, CLICKHOUSE_SECURE, CLICKHOUSE_TLS_MODE, CLICKHOUSE_USER, CLICKHOUSE_VERIFY | 70/100 |
| `io.github.firebase/firebase-mcp` | `0.3.0` | `MIT` (registry-record) | `io.github.firebase` | Yes | `official-vendor` | `stdio` | `npm` | `read-write` | FIREBASE_SERVICE_ACCOUNT_KEY | 70/100 |

### Module 4: Security, Auditing & SecOps
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `io.github.getsentry/sentry-mcp` | `0.49.0` | `MIT` (registry-record) | `io.github.getsentry` | Yes | `official-vendor` | `stdio` | `npm` | `read-write` | SENTRY_AUTH_TOKEN, SENTRY_HOST, SENTRY_URL | 75/100 |
| `io.github.awslabs/mcp-server-for-oscal` | `0.4.0` | `Apache-2.0` (registry-record) | `io.github.awslabs` | Yes | `official-vendor` | `stdio` | `pypi` | `unknown-treat-as-write` | AWS_PROFILE, AWS_REGION, BEDROCK_MODEL_ID, LOG_LEVEL, OSCAL_KB_ID | 70/100 |

### Module 5: AI Architecture, LLM & Prompt Engineering
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `ai.exa/exa` | `3.4.1` | `MIT` (registry-record) | `ai.exa` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-only` | EXA_API_KEY | 75/100 |
| `co.axiom/mcp` | `1.0.0` | `Apache-2.0` (registry-record) | `co.axiom` | Yes | `official-vendor` | `streamable-http` | `remote` | `read-write` | AXIOM_TOKEN | 75/100 |
| `io.github.comet-ml/opik-mcp` | `3.0.9` | `Apache-2.0` (registry-record) | `io.github.comet-ml` | Yes | `official-vendor` | `stdio` | `pypi` | `read-write` | COMET_URL_OVERRIDE, OPIK_API_KEY, OPIK_URL, OPIK_WORKSPACE | 75/100 |

### Module 6: Testing, QA & Reliability Engineering
| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |
|---|---|---|---|:---:|---|---|---|---|---|---|
| `io.github.microsoft/playwright-mcp` | `0.0.84` | `Apache-2.0` (registry-record) | `io.github.microsoft` | Yes | `official-vendor` | `stdio` | `npm` | `read-write` | None | 75/100 |
| `io.github.browserbase/mcp-server-browserbase` | `2.1.1` | `MIT` (registry-record) | `io.github.browserbase` | Yes | `official-vendor` | `stdio` | `npm` | `read-write` | BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID, GEMINI_API_KEY | 70/100 |

## How to Approve
Add the desired exact versions to `DevCrew-Vault/catalog.yaml` under `approvals:`:
```yaml
approvals:
  "com.cloudflare.mcp/mcp": "1.0.0"
  "com.stripe/mcp": "0.2.4"
  "io.github.github/github-mcp-server": "2.1.0"
  "com.figma.mcp/mcp": "1.0.3"
  "com.neon/mcp": "2.0.0"
  "com.supabase/mcp": "0.16.1"
  "io.prisma/mcp": "1.1.0"
  "io.github.ClickHouse/mcp-clickhouse": "0.7.0"
  "io.github.firebase/firebase-mcp": "0.3.0"
  "io.github.getsentry/sentry-mcp": "0.49.0"
  "io.github.awslabs/mcp-server-for-oscal": "0.4.0"
  "ai.exa/exa": "3.4.1"
  "co.axiom/mcp": "1.0.0"
  "io.github.comet-ml/opik-mcp": "3.0.9"
  "io.github.browserbase/mcp-server-browserbase": "2.1.1"
  "io.github.firecrawl/firecrawl-mcp-server": "3.38.0"
  "io.github.modelcontextprotocol/fetch": "0.6.2"
  "io.github.modelcontextprotocol/memory": "2.1.0"
  "io.github.modelcontextprotocol/sequential-thinking": "2.1.1"
  "io.github.modelcontextprotocol/time": "0.6.2"
```

Then re-sync and regenerate client configs:
```bash
python tools/mcp_vet.py
python tools/mcp_config.py --crew devcrew
```