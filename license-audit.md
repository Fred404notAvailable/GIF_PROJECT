# DevCrew Skill Vault — Per-Skill License Audit

This document details the per-skill license audit conducted for all 100 selected skills in the DevCrew AI Skill Vault, distinguishing between folder-level `LICENSE*` files, frontmatter `license:` fields, and repository-level licenses.

## License Resolution Precedence
1. **Skill Folder `LICENSE*`**: Scanned using SPDX signature detection for internal `LICENSE`, `LICENSE.txt`, or `LICENSE.md`.
2. **Frontmatter `license:`**: Declared in `SKILL.md` YAML header (excluding generic pointer text such as `Complete terms in LICENSE.txt`).
3. **Repository Root License**: Recorded in `.source.json` from the upstream repository root.

## Key Audit Findings
- **Anthropic Skills (`anthropics/skills`)**: Corrected from old report claim of `MIT` to verified **`Apache-2.0`** based on internal `LICENSE.txt` present inside each skill package (`mcp-builder`, `frontend-design`, `web-artifacts-builder`, `theme-factory`, `canvas-design`, `webapp-testing`).
- **Trail of Bits Contradiction Resolved**: Skills originating in `trailofbits/skills.git` (`differential-review`, `variant-analysis`, `sharp-edges`, `supply-chain-risk-auditor`, `agentic-actions-auditor`) carry `CC-BY-SA-4.0`. While mirrored by `antigravity-awesome` under an MIT repository wrapper, they were removed from `selected` under strict license adherence and replaced with genuine MIT/Apache-2.0 alternatives.
- **Docker Development (`netresearch/docker-development-skill`)**: Contains dual licensing `(MIT AND CC-BY-SA-4.0)` where documentation and instructions are Share-Alike. Confirmed quarantined in `DevCrew-Vault/_quarantine/` and replaced with official `docker-compose-patterns` and `docker-build-strategies` (Apache-2.0) from `docker/skills`.
- **HashiCorp Agent Skills (`hashicorp/agent-skills`)**: `terraform-policy` is confirmed as **`MPL-2.0`**. `MPL-2.0` is permitted under `devcrew.config.yaml` (`allowed_licenses`).
- **Anton Babenko Terraform Skill**: Replaced aggregator mirror with official upstream `antonbabenko/terraform-skill` (**`Apache-2.0`**).

## Audit Summary Table

| Metric | Value |
|---|---|
| Total Selected Skills | 100 |
| Total Approved (OK) | 100 |
| Total Blocked / Needs-Decision | 0 |
| MIT Licensed | 83 |
| Apache-2.0 Licensed | 16 |
| MPL-2.0 Licensed | 1 |
| Resolved via Skill Folder `LICENSE*` | 8 |
| Resolved via Frontmatter `SKILL.md` | 16 |
| Resolved via Repo Root `.source.json` | 76 |

## Full Per-Skill License Register

| Slot | Module | Skill Slug | Upstream Repository | Repo License | Per-Skill License | License Source | Verdict |
|:---:|:---:|---|---|:---:|:---:|---|:---:|
| 1 | 1 | `api-design-principles` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 2 | 1 | `architecture-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 3 | 1 | `microservices-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 4 | 1 | `dotnet-backend-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 5 | 1 | `nodejs-backend-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 6 | 1 | `fastapi-templates` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 7 | 1 | `workflow-orchestration-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 8 | 1 | `event-store-design` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 9 | 1 | `hono` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 10 | 1 | `cloudflare` | `cloudflare/skills` | Apache-2.0 | **Apache-2.0** | repo root (`.source.json`) | **OK** |
| 13 | 1 | `stripe-best-practices` | `stripe/ai` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 14 | 1 | `mcp-builder` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 200 | 1 | `nodejs-best-practices` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 200 | 1 | `convex` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 200 | 1 | `database-design` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 16 | 2 | `frontend-design` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 17 | 2 | `web-artifacts-builder` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 18 | 2 | `react-best-practices` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 19 | 2 | `next-dev-loop` | `vercel/next.js` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 20 | 2 | `tailwind-design-system` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 21 | 2 | `react-native-best-practices` | `callstackincubator/agent-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 22 | 2 | `frontend-patterns` | `affaan-m/everything-claude-code` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 23 | 2 | `web-ui-shadcn-ui` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 24 | 2 | `angular-best-practices` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 30 | 2 | `ui-visual-validator` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 200 | 2 | `theme-factory` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 200 | 2 | `web-styling-tailwind` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 200 | 2 | `web-tooling-storybook` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 200 | 2 | `canvas-design` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 300 | 2 | `frameworks-on-cloudflare` | `cloudflare/skills` | Apache-2.0 | **Apache-2.0** | repo root (`.source.json`) | **OK** |
| 31 | 3 | `supabase-postgres-best-practices` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 32 | 3 | `supabase` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 33 | 3 | `neon-postgres` | `sickn33/antigravity-awesome-skills` | MIT | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 34 | 3 | `neon-postgres-branches` | `sickn33/antigravity-awesome-skills` | MIT | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 35 | 3 | `prisma-postgres-setup` | `prisma/skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 36 | 3 | `prisma-cli` | `prisma/skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 37 | 3 | `firebase-basics` | `firebase/agent-skills` | Apache-2.0 | **Apache-2.0** | repo root (`.source.json`) | **OK** |
| 38 | 3 | `sql-optimization-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 39 | 3 | `database-migration` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 40 | 3 | `postgresql-table-design` | `wshobson/agents` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 41 | 3 | `clickhouse-best-practices` | `ClickHouse/agent-skills` | Apache-2.0 | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 42 | 3 | `vector-index-tuning` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 43 | 3 | `similarity-search-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 44 | 3 | `hybrid-search-implementation` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 45 | 3 | `embedding-strategies` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 46 | 4 | `security-audit` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 47 | 4 | `secure-webapp` | `hov172/secure-webapp-skill` | MIT | **MIT** | skill folder (`LICENSE*`) | **OK** |
| 48 | 4 | `shared-security-auth-security` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 49 | 4 | `codeql` | `github/awesome-copilot` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 50 | 4 | `semgrep-rule-creator` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 51 | 4 | `stride-analysis-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 52 | 4 | `firebase-security-rules-auditor` | `firebase/agent-skills` | Apache-2.0 | **Apache-2.0** | repo root (`.source.json`) | **OK** |
| 53 | 4 | `api-security` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 54 | 4 | `api-security-testing` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 55 | 4 | `security-auditor` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 56 | 4 | `security-review` | `github/awesome-copilot` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 57 | 4 | `vulnerability-scanner` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 58 | 4 | `web-security-testing` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 59 | 4 | `xss-html-injection` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 60 | 4 | `sql-injection-testing` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 61 | 5 | `prompt-engineering-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 62 | 5 | `rag-implementation` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 63 | 5 | `langchain-architecture` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 64 | 5 | `langgraph-fundamentals` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 65 | 5 | `langgraph-persistence` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 66 | 5 | `langgraph-human-in-the-loop` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 67 | 5 | `langchain-fundamentals` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 68 | 5 | `langchain-rag` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 69 | 5 | `langchain-middleware` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 70 | 5 | `deep-agents-core` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 71 | 5 | `deep-agents-memory` | `langchain-ai/langchain-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 72 | 5 | `autonomous-agent-patterns` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 73 | 5 | `agent-memory-systems` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 74 | 5 | `langfuse` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 75 | 5 | `llm-evaluation` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 76 | 6 | `test-driven-development` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 77 | 6 | `systematic-debugging` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 78 | 6 | `verification-before-completion` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 79 | 6 | `requesting-code-review` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 80 | 6 | `webapp-testing` | `anthropics/skills` | Apache-2.0 | **Apache-2.0** | skill folder (`LICENSE*`) | **OK** |
| 81 | 6 | `web-testing-playwright-e2e` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 82 | 6 | `web-testing-cypress-e2e` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 83 | 6 | `e2e-testing` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 84 | 6 | `observability-engineer` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 85 | 6 | `receiving-code-review` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 86 | 7 | `docker-build-strategies` | `docker/skills` | Apache-2.0 | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 87 | 7 | `docker-compose-patterns` | `docker/skills` | Apache-2.0 | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 88 | 7 | `terraform-skill` | `antonbabenko/terraform-skill` | Apache-2.0 | **Apache-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 89 | 7 | `kubernetes-deployment` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 90 | 7 | `kubernetes-skill` | `LukasNiessen/kubernetes-skill` | MIT | **MIT** | skill folder (`LICENSE*`) | **OK** |
| 91 | 7 | `infra-ci-cd-github-actions` | `agents-inc/skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 92 | 7 | `terraform-policy` | `hashicorp/agent-skills` | MPL-2.0 | **MPL-2.0** | frontmatter (`SKILL.md`) | **OK** |
| 93 | 7 | `aws-cdk-development` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 94 | 7 | `cloud-devops` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 95 | 7 | `aws-serverless` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 96 | 7 | `azure-devops` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 97 | 7 | `devops-deploy` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 98 | 7 | `aws-serverless-eda` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | frontmatter (`SKILL.md`) | **OK** |
| 99 | 7 | `application-performance-performance-optimization` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
| 100 | 7 | `bash-linux` | `sickn33/antigravity-awesome-skills` | MIT | **MIT** | repo root (`.source.json`) | **OK** |
