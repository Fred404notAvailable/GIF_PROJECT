# Fix Prompt (Round 2): Provenance, Licenses, Full Registry Coverage, and Honest Safety Labels

## Context
The previous fix round removed the irrelevant MCP servers and the pairing padding, and the safety gates still pass (no code executed, no secrets stored, no auto-approval). An independent review of the new `RESULT-REPORT.md` found problems that still need fixing. Work in the existing project. Do not rebuild what works (watcher, map layer, tests, gates).

Read the current code, `devcrew.config.yaml`, `catalog.yaml`, `registry.db`, and the existing reports first.

## Ground Rules
1. **Every number in the rewritten reports must come from a query or file check run in this session.** If a claim cannot be verified, say so.
2. **Unknown means unsafe.** Anywhere a safety attribute is `unknown`, treat the server as the riskiest plausible value (see Problem 5).
3. **Do not decide license policy for the user.** Anything outside `allowed_licenses` is not counted as `selected` until the user adds it. Put the decision in `DECISIONS-NEEDED.md`.
4. **No server code is installed or executed. No secrets stored. The agent never approves a server.**
5. **Never fabricate** servers, versions, publishers, or skill sources. If something is not found, say `not found` with the exact query used.
6. Keep existing tests passing and add new ones (fixtures only, no live network in tests).

---

## Problem 1: Skills were swapped for aggregator mirrors
About 59 of the 100 selected skills now show `antigravity-awesome` as their source, including skills pinned to other upstream repos (for example `api-design-principles`, `microservices-patterns`, `architecture-patterns`, `workflow-orchestration-patterns`, `test-driven-development`, `systematic-debugging`, `requesting-code-review`, `react-best-practices`, `supabase`, `supabase-postgres-best-practices`, `neon-postgres`, `rag-implementation`, `prompt-engineering-patterns`, `tailwind-design-system`). `postgresql-table-design` still shows `wshobson-agents`, so the result is inconsistent. A likely cause is that the aggregator is first in the sync order and wins slug collisions.

### Fix
1. Print the real count per `source_name` for selected skills (`SELECT s.source_name, COUNT(*) ... GROUP BY 1`) and list every selected skill whose source is an aggregator (`antigravity-awesome`, `awesome-copilot`, `everything-claude-code`, or any repo that mirrors others).
2. **Source preference rule.** For each selected slug, prefer the **original upstream** over any aggregator copy. Change collision handling so that when the same slug exists in multiple sources, rank in this order: (a) the repo named in the pinned list in `catalog.yaml`, (b) the vendor or original author's repo, (c) any aggregator. Aggregators never win a collision against a pinned or original source.
3. Where the original upstream copy exists in the staging clones, re-point the selected slot to it (namespacing the aggregator copy as `antigravity-awesome--<slug>` and keeping it as `alternate`). Re-validate the upstream copy and re-run the license gate on it.
4. Where the original does not exist or fails validation, keep the aggregator copy but mark it `provenance: aggregator-mirror`, record which upstream it appears to originate from (from its frontmatter, README, or `.source.json`) if determinable, and list it in the report.
5. For each remaining aggregator-sourced selected skill, compare its content hash against the upstream copy when one exists. Report any whose content differs from upstream.
6. Report the before/after source distribution.

## Problem 2: An MPL-2.0 skill was selected without a decision
`terraform-policy` (HashiCorp, MPL-2.0) is `selected`, but MPL-2.0 was supposed to wait for a user decision. The old report did not mention it.

### Fix
1. Print the `allowed_licenses` list currently in `devcrew.config.yaml` and explain exactly how MPL-2.0 became allowed (which commit, file, or code path). If the agent added it, revert that change.
2. Re-run the consistency check so that **no selected skill or MCP server has a license outside `allowed_licenses`**. Any that fail become `unfilled`, and their slot is filled from alternates or left short.
3. Also check per-skill license vs repo license for every selected skill (a skill with its own `LICENSE` file or `license:` frontmatter that differs from the repo label must be judged on its own license). Write `license-audit.md` again with the verified results.
4. Update `DECISIONS-NEEDED.md` with a clear choice for MPL-2.0 (allow or not), listing exactly which selected items depend on it.

## Problem 3: The MCP registry was probed, not ingested
The report says the registry contains 58,646 servers across 587 pages, but only about 427 servers were ever considered. That is under 1%. The number may also include many old versions, since earlier sources suggested roughly 9,400 public servers in April 2026.

### Fix
1. **Ingest the full registry.** Paginate to the end with `version=latest` (and, separately, report the count when versions are included, so the 58,646 figure can be explained). Store every record's key fields in the database as `candidate` (raw snapshots stay under `mcp-registry/raw/`, which is already excluded from Obsidian). Report: pages fetched, records fetched, records unique by name, records skipped as invalid, and whether pagination completed. If the run is interrupted, resume from the last cursor.
2. Do vetting and relevance scoring **over all ingested candidates**, not a subset. Cheap checks first (relevance, exclude list, namespace), then repo enrichment only for survivors, to stay within GitHub rate limits. Cache everything.
3. Report how many candidates passed each gate (relevance, developer-tool fit, vetting floor) so the funnel is visible.

## Problem 4: Seed lookups look wrong
GitHub, Docker, AWS, and Prisma were reported `not in registry`. GitHub and AWS both publish MCP servers, so this needs a direct re-check.

### Fix
1. For each seed, run **multiple** lookups and record every query and its result count in `MCP-SEED-RESULTS.md`:
   - registry search by name (for example `github`, `aws`, `docker`, `prisma`, `supabase`, `sentry`, `playwright`, `e2b`, `browserbase`)
   - registry search by publisher namespace (for example `io.github.github`, `com.github`, `io.github.awslabs`, `com.amazon`, `io.github.docker`, `com.docker`, `io.github.prisma`)
   - lookup by known repo URL (`github/github-mcp-server`, `awslabs/mcp`, `docker/mcp-*`, `prisma/prisma`)
2. A seed is `not in registry` only if **all** lookups return nothing. If a repository exists on GitHub but is not in the registry, record `not-in-registry (repo: <url>)`.
3. Fix the arithmetic in the seed table: the count of "ambiguous" seeds must equal the number actually listed.
4. If the official Playwright server (`microsoft/playwright-mcp`, usually the local `@playwright/mcp` package) exists in the registry, prefer it over `playwright-cloud-browsers`. Explain what `playwright-cloud-browsers` is (local or hosted) before selecting it.

## Problem 5: Safety labels were wrong or `unknown`
- 14 of the 20 selected servers have `capability_class = unknown`, including filesystem, Stripe, Cloudflare, Terraform, and Kubernetes, all of which can plausibly write or change things.
- The reference `git` server was labeled `read-only` but, as far as known, includes write tools (such as add, commit, reset, branch). Verify against the repo.
- Several servers were marked as requiring no secrets (Stripe, Cloudflare, Neon, Figma) although they typically need API keys or OAuth.
- The Kubernetes server comes from the `containers` GitHub organization but was labeled `official-vendor`.
- The publisher column showed the same generic text for every row.

### Fix
1. **Capability classification from evidence.** For each selected or proposed server, read the registry record and the repo README / tool list (static inspection only) and classify as `read-only`, `read-write`, or `destructive`, recording the evidence (tool names found). If the tools cannot be determined, set `capability_class = unknown-treat-as-write`, and treat it in every rule as `read-write`. Never label a server `read-only` unless every discovered tool is read-only. Re-check `git`, `filesystem`, `memory`, `time`, `fetch`, `everything`, `sequential-thinking`.
2. **Secrets from evidence.** Derive required environment variables, OAuth, or API key needs from the registry record's package and remote definitions (environment variable and header fields) and the README. If a service needs authentication, `requires_secrets` must be true, with the variable names listed. Mark `unverified` where undeterminable, never `No`.
3. **Maintainer class from evidence.** `official-vendor` requires the namespace to be verified and to match the vendor's own domain or GitHub org (for example the `hashicorp` org for Terraform). A repository under another org with a similar name is `community`. Record the registry's publisher/namespace and the repo owner as separate fields, and show real values in the report (not templated text).
4. **Remove unsuitable selections:** `everything` (a reference test server) must not be `selected`; keep it as `candidate`. Reassess module placement so servers appear under the module they truly serve (for example `filesystem` and `time` are general utilities, not Database; `firecrawl` and `context7` are not DevOps). Introduce a `General / Utilities` placement (outside the 7 modules, no target) for cross-cutting servers such as filesystem, git, fetch, time, memory, and documentation servers.
5. Add a **combination risk note** to `MCP-APPROVALS-NEEDED.md` for any approved set that includes git plus filesystem, or fetch plus any write-capable server.

## Problem 6: Smaller report and logic errors
1. **Pairing bug.** `stripe-mcp` has 0 pairs even though the selected skill `stripe-best-practices` exists and `Stripe` is a strong-signal tag. Debug the tag assignment and pairing rule, fix it, and add a test that a Stripe server pairs with the Stripe skill. Rebuild `pairs-with` links and the map.
2. **Slot numbering.** The skill tables restart at slot 1 in each module, so the 100 pinned slots (1-100) cannot be traced. Generate the skill tables with the **global slot number** from the pinned list (and `unlisted` for skills not in the pinned list), alongside a column showing whether the selected skill matches the pinned slug, is a documented replacement, or is a mirror.
3. **Pinned-list reconciliation.** Add a table: pinned slot, expected slug, actual selected slug, source, status (`matched`, `renamed`, `replaced`, `unfilled`). List every selected skill that is not in the pinned list, with the reason it replaced a pinned entry.
4. **Maintainer vs. source wording.** Replace the phrase "Official Vendor / Reference" in the server table with the real publisher namespace and verification status per row.

---

## Tests (fixtures only)
Add or update tests for:
- Collision preference: pinned/original source beats an aggregator; aggregator copy becomes `alternate`.
- License gate: a skill or server with MPL-2.0 (or any license not in `allowed_licenses`) is never `selected`.
- Capability rules: unknown capability is treated as write-capable; a server with any write tool is never `read-only`.
- Secrets detection from registry `environmentVariables` / headers.
- Maintainer class: org mismatch yields `community`.
- Pagination completes, resumes after interruption, and reports incomplete runs honestly.
- Seed lookup does not report `not in registry` unless all lookups were empty.
- Stripe server pairs with the Stripe skill.
- Report tables are generated from the database (spot-check slot numbers and counts).
Run the full suite, `verify_vault.py`, and `build_map.py --check`, and report the real results.

## Deliverables
1. Updated sync, collision, license, vetting, capability, and pairing code, plus config changes (`allowed_licenses` restored to the user's setting, source preference order).
2. Updated `license-audit.md` and `DECISIONS-NEEDED.md` (MPL-2.0 decision).
3. Full-registry ingestion results and a candidate funnel table.
4. Rewritten `MCP-SEED-RESULTS.md` with every query listed.
5. Rewritten `MCP-APPROVALS-NEEDED.md` with evidence-based capability, secrets, and maintainer data, plus combination risk notes. `approvals:` stays empty unless the user has filled it in.
6. Rebuilt map layer.
7. Rewritten `RESULT-REPORT.md` with: a "Corrections to the previous report" section covering each problem above; source distribution before and after; the pinned-slot reconciliation table; the funnel; honest shortfalls. It must not claim a quota is met or labels are verified unless the data supports it.
8. A final summary of what changed, what is still short, and the decisions the user must make.
