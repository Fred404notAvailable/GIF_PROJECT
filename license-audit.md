# DevCrew Skill Vault — Per-Skill License Audit

> [!NOTE]
> Verified license audit conducted across all selected skills in the DevCrew AI Skill Vault.
> Audits distinguish between folder-level `LICENSE*` files, frontmatter `license:` declarations, and repository-level licenses.

**Audit Timestamp:** 2026-11-08 14:51:22 UTC
**Total Selected Skills Evaluated:** 99
- **MIT Licensed:** 83
- **Apache-2.0 Licensed:** 16
- **MPL-2.0 Licensed (Selected):** 0 (0 — MPL-2.0 omitted pending user decision)
- **Unfilled Pinned Slots:** 1 (Slot 92 `terraform` / HashiCorp `terraform-policy` is MPL-2.0)

## Key Audit Findings

1. **Zero Unapproved Licenses in Selected:**
   No selected skill or MCP server carries a license outside `devcrew.config.yaml` `allowed_licenses` (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `CC-BY-4.0`).

2. **MPL-2.0 Slot 92 Policy Decision:**
   HashiCorp's `terraform-policy` is MPL-2.0. Following Ground Rule 3, the agent does not decide license policy for the user.
   Slot 92 has been reverted to `unfilled` and recorded in `DECISIONS-NEEDED.md`. Total selected is 99/100 (shortfall: 1).

3. **Anthropic Skills (`anthropics/skills`):**
   Verified as **`Apache-2.0`** based on internal package-level `LICENSE.txt` files (`mcp-builder`, `frontend-design`, `web-artifacts-builder`, `theme-factory`, `canvas-design`, `webapp-testing`).

4. **Provenance & Source Preference Applied:**
   31 skills were re-pointed from aggregator mirrors (`antigravity-awesome`, `awesome-copilot`) to genuine upstream author repositories
   (`wshobson-agents`, `obra-superpowers`, `supabase`, `neon`, `convex`, `aws-skills`).

## Audit Summary Statistics

| Metric | Count | Percentage |
|---|:---:|:---:|
| **Total Selected Skills** | **99** | 100.0% |
| **MIT License** | 83 | 83.8% |
| **Apache-2.0 License** | 16 | 16.2% |
| **Unapproved Licenses in Selected** | **0** | **0.0%** |
| **Unfilled Slots (Awaiting Decision)** | **1** (Slot 92, MPL-2.0) | N/A |

## Full Per-Skill License Register

| Slot | Module | Skill Slug | Source Repository | Repo License | Per-Skill License | License Source | Verdict |
|:---:|:---:|---|---|:---:|:---:|---|:---:|
| 1 | 1 | `api-design-principles` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 2 | 1 | `architecture-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 3 | 1 | `microservices-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 4 | 1 | `dotnet-backend-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 5 | 1 | `nodejs-backend-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 6 | 1 | `fastapi-templates` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 7 | 1 | `workflow-orchestration-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 8 | 1 | `event-store-design` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 9 | 1 | `hono` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 10 | 1 | `cloudflare` | `cloudflare` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 13 | 1 | `stripe-best-practices` | `stripe` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 14 | 1 | `mcp-builder` | `anthropic-skills` | Apache-2.0 | **Apache-2.0** | skill folder (LICENSE*) | **OK** |
| 16 | 2 | `frontend-design` | `anthropic-skills` | Apache-2.0 | **Apache-2.0** | skill folder (LICENSE*) | **OK** |
| 17 | 2 | `web-artifacts-builder` | `anthropic-skills` | Apache-2.0 | **Apache-2.0** | skill folder (LICENSE*) | **OK** |
| 18 | 2 | `react-best-practices` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 19 | 2 | `next-dev-loop` | `nextjs-official` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 20 | 2 | `tailwind-design-system` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 21 | 2 | `react-native-best-practices` | `callstack-rn` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 22 | 2 | `frontend-patterns` | `everything-claude-code` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 23 | 2 | `web-ui-shadcn-ui` | `agents-inc` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 24 | 2 | `angular-best-practices` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 25 | 2 | `server-actions` | `szum-tech` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 26 | 2 | `react-19-compiler` | `szum-tech` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 27 | 2 | `tailwind-css-4` | `szum-tech` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 30 | 2 | `ui-visual-validator` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 31 | 3 | `supabase-postgres-best-practices` | `supabase` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 32 | 3 | `supabase` | `supabase` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 33 | 3 | `neon-postgres` | `neon` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 34 | 3 | `neon-postgres-branches` | `antigravity-awesome` | MIT | **Apache-2.0** | repo root (.source.json) | **OK** |
| 35 | 3 | `prisma-postgres-setup` | `prisma` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 36 | 3 | `prisma-cli` | `prisma` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 37 | 3 | `firebase-basics` | `firebase` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 38 | 3 | `sql-optimization-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 39 | 3 | `database-migration` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 40 | 3 | `postgresql-table-design` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 41 | 3 | `clickhouse-best-practices` | `clickhouse` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 42 | 3 | `vector-index-tuning` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 43 | 3 | `similarity-search-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 44 | 3 | `hybrid-search-implementation` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 45 | 3 | `embedding-strategies` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 47 | 4 | `security-audit` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 48 | 4 | `secure-webapp` | `secure-webapp` | MIT | **MIT** | skill folder (LICENSE*) | **OK** |
| 49 | 4 | `owasp-audit` | `cybersecurity-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 59 | 4 | `firebase-security-rules-auditor` | `firebase` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 60 | 4 | `stride-analysis-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 61 | 5 | `prompt-engineering-patterns` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 62 | 5 | `rag-implementation` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 63 | 5 | `langchain-architecture` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 64 | 5 | `langgraph-fundamentals` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 65 | 5 | `langgraph-persistence` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 66 | 5 | `langgraph-human-in-the-loop` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 67 | 5 | `langchain-fundamentals` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 68 | 5 | `langchain-rag` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 69 | 5 | `langchain-middleware` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 70 | 5 | `deep-agents-core` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 71 | 5 | `deep-agents-memory` | `langchain-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 72 | 5 | `autonomous-agent-patterns` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 73 | 5 | `agent-memory-systems` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 74 | 5 | `langfuse` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 75 | 5 | `llm-evaluation` | `wshobson-agents` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 76 | 6 | `test-driven-development` | `obra-superpowers` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 77 | 6 | `systematic-debugging` | `obra-superpowers` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 78 | 6 | `verification-before-completion` | `obra-superpowers` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 79 | 6 | `requesting-code-review` | `obra-superpowers` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 80 | 6 | `webapp-testing` | `anthropic-skills` | Apache-2.0 | **Apache-2.0** | skill folder (LICENSE*) | **OK** |
| 83 | 6 | `e2e-testing` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 85 | 6 | `observability-engineer` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 90 | 7 | `kubernetes-skill` | `kubernetes-skill` | MIT | **MIT** | skill folder (LICENSE*) | **OK** |
| 91 | 7 | `terraform-skill` | `terraform-skill` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| 99 | 7 | `application-performance-performance-optimization` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| 100 | 7 | `bash-linux` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 1 | `nodejs-best-practices` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 1 | `convex` | `convex` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| unlisted | 1 | `database-design` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 2 | `theme-factory` | `anthropic-skills` | Apache-2.0 | **Apache-2.0** | skill folder (LICENSE*) | **OK** |
| unlisted | 2 | `frameworks-on-cloudflare` | `cloudflare` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| unlisted | 4 | `shared-security-auth-security` | `agents-inc` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `semgrep-rule-creator` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `api-security` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `api-security-testing` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `security-auditor` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `security-review` | `awesome-copilot` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `vulnerability-scanner` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `web-security-testing` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `xss-html-injection` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 4 | `sql-injection-testing` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 6 | `web-testing-playwright-e2e` | `agents-inc` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 6 | `web-testing-cypress-e2e` | `agents-inc` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 6 | `receiving-code-review` | `obra-superpowers` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `docker-build-strategies` | `docker-skills` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| unlisted | 7 | `docker-compose-patterns` | `docker-skills` | Apache-2.0 | **Apache-2.0** | repo root (.source.json) | **OK** |
| unlisted | 7 | `kubernetes-deployment` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `infra-ci-cd-github-actions` | `agents-inc` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `aws-cdk-development` | `aws-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `cloud-devops` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `aws-serverless` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `azure-devops` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `devops-deploy` | `antigravity-awesome` | MIT | **MIT** | repo root (.source.json) | **OK** |
| unlisted | 7 | `aws-serverless-eda` | `aws-skills` | MIT | **MIT** | repo root (.source.json) | **OK** |
