# Fix Prompt: Correct the MCP Catalog Selection and the Master Report

## Context
The MCP catalog build passed its safety gates (no code executed, no secrets stored, no auto-approval, 59 tests passing, zero dangling map links). An independent review of `RESULT-REPORT.md` found real problems in the **MCP selection quality** and some report claims that need checking. Fix them in the existing project. Do not rebuild what works (skills vault, map layer, watcher, safety gates).

Read the current code, `catalog.yaml`, `registry.db`, and the existing reports first.

## Ground Rules
1. **Trust data, not the old report.** Every number in the rewritten report must come from a query or file check you ran in this session.
2. **Relevance and safety beat quotas.** Do not fill module slots with servers just because a keyword matched. A module with few credible servers stays short, and that is a correct result.
3. **No server code is installed or executed.** No secrets are stored. The agent never approves a server; approvals only come from the user via `catalog.yaml`.
4. **No invented data.** If a server, version, or skill name cannot be found in the registry, repo, or database, say so.
5. Keep existing tests passing and add new ones. Use fixture JSON, not the live network, in tests.

---

## Problem 1: Irrelevant servers were selected
The old selection included servers unrelated to their modules, for example `contractor-license-changes` and `thirdhemisphere-ai-authority-index` (Backend), `business-contact-finder` and `1clickwebsite` (Frontend), `beachclubs` and `aeoengine-report` (Database), `lona-trading` and `atmy-air-quality` (AI). They matched loose keywords.

### Fix
1. **Replace quota-driven selection with threshold-driven selection.** A server may become `selected` only if **all** of these hold:
   - **Relevance:** its title, description, and package name score above a documented minimum for its module using a tightened keyword set (require at least 2 distinct module keywords, or 1 keyword from a strong-signal list such as `postgres`, `playwright`, `kubernetes`, `github`, `terraform`, `docker`, `owasp`, `semgrep`). Generic words like `api`, `data`, `agent`, `search`, `build` must not count on their own.
   - **Developer-tool fit:** exclude servers whose purpose is clearly non-developer (trading, air quality, business contacts, licensing news, directory listings, marketing, lead generation, entertainment, and similar). Maintain this as an `mcp_exclude_keywords` list in `catalog.yaml`.
   - **Vetting floor:** vetting score at or above a documented minimum, a verified namespace or official-vendor/reference maintainer class, an actively maintained repo (not archived), a license in `allowed_licenses`, and a pinned (non-`latest`) version.
2. **Treat module targets as ceilings, not goals.** Keep `mcp_targets` in `catalog.yaml` but select **up to** the target. Report the shortfall per module honestly.
3. Re-run selection and print, for every previously selected server that is now dropped, the reason (which rule failed). Keep dropped servers as `candidate` (or `retired` if archived/invalid); do not delete.

## Problem 2: The registry sync was incomplete
The old report says "first 400 registry records" (plus 13 reference servers). None of the expected vendor servers (GitHub, Supabase, Neon, Figma, Sentry, Context7, Cloudflare, Stripe, Playwright, Docker, Terraform, AWS, Kubernetes) appeared in the selection.

### Fix
1. Remove any default `--limit` cap. Paginate the **entire** registry using the API's cursor/pagination (read `/docs` for the current version path and fields), with `version=latest`. Respect rate limits, back off on errors, and resume safely if interrupted.
2. Record in `mcp_sync` output: total records the registry reports (if given), total fetched, pages fetched, and whether pagination completed. If it did not complete, say so and do not report coverage as complete.
3. **Seed-first search.** Before general ranking, look up each seed by registry search (`search=<term>`) and by exact repo URL. Seeds to look up: GitHub (official), Playwright (Microsoft), Supabase, Neon, ClickHouse, Prisma, Firebase, Figma, Sentry, Context7, Cloudflare, Stripe, Docker, Terraform (HashiCorp), AWS (official), Kubernetes, filesystem, git, fetch, memory, sequential-thinking, time, Browserbase, E2B, Exa, Firecrawl, Axiom, Comet Opik. For each seed record one of: `found (<registry name>, <version>)`, `not in registry`, or `ambiguous (<candidates>)`. Put this in a `MCP-SEED-RESULTS.md` table.
4. Where a seed exists on GitHub but not in the registry, record the repo and mark it `not-in-registry` (a candidate for manual review, not auto-selected).

## Problem 3: Skill-to-server pairing was noise
Exactly 120 pair links equals 40 servers times the cap of 3, which means every server hit the cap.

### Fix
1. Pair a server with a skill only when they share **at least 2 tech tags**, or 1 tag from the strong-signal list (for example a Supabase server and a Supabase skill). Rank by number of shared tags and keep at most 3 per server, but **do not fill up to the cap**; fewer links is correct.
2. A server with no valid pairing has zero pairs. Report how many servers have 0, 1, 2, and 3 pairs.
3. Rebuild the `pairs-with` links, then rebuild the map layer.

## Problem 4: The report's skill names may not match the database
The report's module breakdown lists names such as `hono-routing`, `owasp-top-10`, `zero-trust`, `langgraph-design`, `rag-architecture`, `react-patterns`, `supabase-patterns`, and `web-testing-cypress-e2e`. The pinned target list used different names (for example `hono`, `stride-analysis-patterns`, `langgraph-fundamentals`, `react-best-practices`, `supabase`).

### Fix
1. Generate the module breakdown **directly from the database** (`skill_modules` joined to `skills`), listing real slugs and their source repos. Do not write it by hand.
2. Compare the real selected slugs against the pinned list in `catalog.yaml` (slot, expected slug, matched upstream slug). Print a table of matches, renames, and `unfilled` slots. Flag any selected skill that is not in the pinned list and is not a documented replacement.
3. If any names in the old report do not exist in the database, list them under "Corrections to the previous report".

## Problem 5: Approval suggestions need verification
The old report suggests pins: fetch 0.6.2, git 0.6.2, filesystem 2.2.0, memory 2.1.0, sequential-thinking 2.1.1.

### Fix
1. For every server proposed for approval, verify the **exact registry name, version, package type, and repository** from the stored registry snapshot. If a proposed pin is not present in the snapshot, remove it and say why.
2. Rewrite `MCP-APPROVALS-NEEDED.md` so each entry shows: registry name, exact pinned version, publisher and whether the namespace is verified, maintainer class, transport, package type, capability class, secrets required, vetting score and notes, and the exact YAML line to add to `catalog.yaml`.
3. Add risk notes where relevant, for example:
   - **filesystem:** must be scoped to the project workspace only; show the argument that restricts the path.
   - **fetch:** returns untrusted web content (prompt-injection risk); recommend a human-approval gate.
   - **git + filesystem together:** combined servers widen the attack surface; recommend that write operations pass through a human-approval gate.
   - Any server whose capability class is `read-write` or `destructive` must say so prominently.
4. Do not approve anything. Leave `approvals:` empty unless the user has already filled it in.

---

## Verification and Tests
Add or update tests (fixture data only):
- Selection excludes servers that fail relevance, developer-tool fit, or the vetting floor, even when a module is under target.
- Generic keywords alone never qualify a server.
- Pagination follows cursors to completion, resumes after an interruption, and reports incomplete runs honestly.
- Pairing requires 2 shared tags (or 1 strong-signal tag) and does not fill to the cap.
- Module breakdown in the generated report matches the database exactly.
- `MCP-APPROVALS-NEEDED.md` only lists versions present in the stored snapshot.
Run the full suite and report the real count. Re-run `verify_vault.py` and `build_map.py --check`.

## Deliverables
1. Updated `mcp_sync.py`, `mcp_vet.py`, selection and pairing logic, and `catalog.yaml` (`mcp_exclude_keywords`, strong-signal list, thresholds).
2. `MCP-SEED-RESULTS.md` (seed lookup outcomes).
3. Rebuilt map layer and `MCP-REPORT.md` with: full-registry coverage numbers, selected-per-module versus ceiling, dropped servers with reasons, pairing distribution, and open decisions.
4. Rewritten `MCP-APPROVALS-NEEDED.md` with verified pins and risk notes.
5. Rewritten `RESULT-REPORT.md` with a "Corrections to the previous report" section covering: the irrelevant selections, the incomplete sync, the pairing cap artifact, any wrong skill names, and any unverified pins. The report must not claim a quota was "met" unless every selected item passes the relevance and vetting rules.
6. A final summary of what changed, what is still short, and what the user must decide.
