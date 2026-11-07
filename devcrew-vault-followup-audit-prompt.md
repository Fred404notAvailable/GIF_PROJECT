# Follow-Up Prompt: Audit, Correct, and Harden the DevCrew Vault

## Context
The vault expansion is done and `RESULT-REPORT.md` claims 100/100 selected skills, 4,155 indexed packages, 501 quarantined, and 31 passing tests. An independent review found several inconsistencies and risks in that report. Your job is to **verify the claims against the actual data, fix what is wrong, and rewrite the report so it matches reality.**

Work in the existing project (`d:\UPS_project`). Do not rebuild anything that works. Read the current code, config, `catalog.yaml`, and `registry.db` first.

## Ground Rules
1. **Trust the data, not the report.** Every number and claim in the new report must come from a query or file check you ran in this session. If a claim in the old report is wrong, say so plainly.
2. **Do not silently change license policy.** Any decision about allowing a license (CC-BY-SA-4.0, MPL-2.0, or another) goes into `DECISIONS-NEEDED.md` for the user. Until the user answers, apply the **stricter** reading: do not count a skill as `selected` if its license is not currently in `allowed_licenses`.
3. **Never fabricate or hand-write skills** to fill a slot. A slot that cannot be filled legitimately stays `unfilled`.
4. **Never execute code from ingested skills.** Static inspection only.
5. Keep all scripts idempotent and keep the existing test suite passing.

---

## Task 1: Reconcile "selected" with reality
1. Print the current `allowed_licenses`, `on_unknown_license`, and `on_slug_collision` from `devcrew.config.yaml`. Compare against `RESULT-REPORT.md` and note every mismatch (for example whether MPL-2.0, CC-BY-SA-4.0, Apache-2.0, or BSD-3-Clause are allowed).
2. For every skill with `skill_modules.status = 'selected'`, verify all of the following, and list any that fail:
   - the folder exists under `DevCrew-Vault/skills/` (not `_quarantine/`)
   - `validation_status` is `valid` or `valid-with-warnings`
   - its license (per-skill value, falling back to the repo license) is in `allowed_licenses`
   - `.source.json` exists and has `repo_url`, `commit_sha`, `license`, and `content_sha256`
3. **Known suspected contradiction:** the old report lists `trailofbits` as quarantined (CC-BY-SA-4.0), yet slots 47-52 (differential-review, codeql, variant-analysis, sharp-edges, supply-chain-risk-auditor, agentic-actions-auditor) are marked selected from it. Determine which is true. Either those six are legitimately allowed (then explain how and when the license was approved) or they are quarantined and must be removed from `selected`.
4. Any selected skill that fails a check becomes `unfilled`. Recompute the real `selected/target` per module.

Suggested starting queries (adapt to the actual schema):
```sql
SELECT m.module_id, m.status, COUNT(*) FROM skill_modules m GROUP BY 1,2;
SELECT s.slug, s.source_name, s.license, s.validation_status
FROM skills s JOIN skill_modules m ON m.slug = s.slug
WHERE m.status = 'selected' AND (s.validation_status = 'invalid' OR s.license IS NULL OR s.license NOT IN (<allowed_licenses>));
SELECT s.license, COUNT(*) FROM skills s JOIN skill_modules m ON m.slug = s.slug
WHERE m.status = 'selected' GROUP BY 1;
```

## Task 2: License Provenance Audit (per skill, not per repo)
1. For each of the selected skills, determine the license from, in order: the skill folder's own `LICENSE*`, the `license:` frontmatter field, then the repo root license. Record which source was used.
2. Flag every case where the per-skill license **differs** from the repo-level label in the old report. Specifically check:
   - `anthropics/skills` (individual skills may carry their own license files; some are source-available, not open source)
   - `netresearch/docker-development-skill` (code MIT, content CC-BY-SA-4.0)
   - `hashicorp/agent-skills` (reported as MPL-2.0; confirm and decide whether it is allowed)
   - any skill that comes from the `antigravity-awesome` aggregator but originated in another repo (a mirror may carry the wrong license; trace the original source where `.source.json` or the skill body names it)
3. Write `license-audit.md`: a table of selected skills with slug, repo, per-skill license, license source, and an `OK / needs-decision / blocked` verdict.

## Task 3: Re-test the "404" Repositories
The old report lists these as HTTP 404: `hannsxpeter/secauditor`, `ComposioHQ/awesome-claude-skills`, `antonbabenko/terraform-skill`, `blastum/AgentSkills`, `remcovergoossen/q24devops`. Also check whether `hov172/secure-webapp-skill` and `docker/skills` were synced as expected.
1. Retry each with `git ls-remote` using the exact URL, then try common variants (case differences, a renamed owner or repo, a `.git` suffix) and a GitHub search for the repo name.
2. For each repo, record one of: `works now`, `renamed to <new url>`, `really gone`, `private or blocked`, or `network error` (retry later). Include the exact error text. A transient network failure must not be reported as "missing".
3. If a repo is reachable, sync it through the normal pipeline and re-run validation and the license gate.
4. In particular, check whether `terraform-skill` in slot 88 (currently from the aggregator mirror) can come from the original upstream repo instead.

## Task 4: Replace Weak Slots
1. Review every selected skill in the context of its module. Flag a slot as **weak** if any of these hold: off-topic for the module (for example `solidity-security`, `redis-security`, `spring-security` padding Security; `dispatching-parallel-agents`, `temporal-python-testing` padding Testing; `extension-to-functions-codebase` in DevOps), thin or generic content, low-quality aggregator origin, or a near-duplicate of another selected skill.
2. Replace weak slots, in this order: (a) the module's alternates from the continuation prompt, (b) skills freshly unlocked by Task 3, (c) other validated candidates ranked by the existing scoring, (d) candidates found via `discovery_indexes`.
3. **Priority gaps to fill:**
   - Security: at least one dedicated OWASP Top 10 skill (check `hov172/secure-webapp-skill`, `briiirussell/cybersecurity-skills` `owasp-audit`, `hannsxpeter/secauditor`).
   - DevOps: a real GitHub Actions / CI-CD skill and a Helm skill from a reputable source; AWS, Azure, or GCP infrastructure skills that are not aggregator mirrors.
   - Testing: more core testing skills (unit, integration, load, accessibility) in place of orchestration or Temporal-specific ones.
4. For every replacement, record the old skill, the new skill, and a one-line reason. Keep replaced skills as `candidate`, never delete them.
5. If a module cannot reach its target legitimately, leave it short and report the shortfall.

## Task 5: Fill the Test Gaps
The old test run covered classification, coverage, ranking, module sync, and the validator only. Add tests (using local fixture repos, no network) for:
- **Sync:** collision namespacing, unchanged-skip by hash, license gate (allowed / unknown / disallowed), atomic replace on change, one failing source not aborting the others.
- **Watcher:** create, edit, rename, delete, rapid repeated saves (debounce), invalid edit then fix, ignored temp files, and `.obsidian/` changes ignored.
- **Provenance:** every selected skill has a complete `.source.json`.
- **Consistency check (new):** a test or `python tools/verify_vault.py` command that fails if any `selected` skill is in `_quarantine/`, is invalid, or has a license outside `allowed_licenses`. Run it as part of `pytest`.
Run the full suite and report the real count.

## Task 6: Decisions File
Create `DECISIONS-NEEDED.md` for the user, with the default you applied and the impact of each choice:
1. **CC-BY-SA-4.0** (Trail of Bits and `docker-development` content): allow or not. List exactly which selected skills depend on it.
2. **MPL-2.0** (HashiCorp): allow or not. List affected skills.
3. **Unlicensed repos** (`better-auth`, `claudekit`, `opencode-configs`, `modernstack`, and any others): keep quarantined, or contact the maintainers. List the slots that would be filled if allowed.
4. **Per-skill license exceptions** found in Task 2.
For each, show how many slots would be filled or lost under both answers.

## Task 7: Rewrite the Report
Replace `RESULT-REPORT.md` with an honest, data-backed version containing:
- Real `selected/target` per module (after Tasks 1-4), with `unfilled` slots listed.
- A "Corrections to the previous report" section listing every claim that changed and why.
- The license audit summary and link to `license-audit.md`.
- The 404-repo outcomes from Task 3.
- Replacement log from Task 4.
- Real test count and results from Task 5, including the new consistency check.
- Open decisions pointing to `DECISIONS-NEEDED.md`.
- Total ingested and quarantined counts, recomputed from the database and filesystem (not copied from the old report).
Do not use "100% target met" unless every selected skill passes the Task 1 checks.

## Deliverables Checklist
- [ ] Reconciliation of `selected` vs. actual state, Trail of Bits contradiction resolved
- [ ] `license-audit.md` (per-skill licenses)
- [ ] Re-tested repositories with exact outcomes
- [ ] Weak slots replaced, or shortfalls reported
- [ ] New sync, watcher, provenance, and consistency tests passing
- [ ] `DECISIONS-NEEDED.md`
- [ ] Rewritten `RESULT-REPORT.md` with corrections section
