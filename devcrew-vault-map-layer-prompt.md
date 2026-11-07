# Prompt: Build the Obsidian Map Layer for the DevCrew Vault

## Context
The vault works but is unreadable in Obsidian's graph view: thousands of unlinked skill files form a huge ring of loose dots around a dense knot of internal reference links. Only the ~100 **selected** skills matter day to day. Build a generated "map layer" so the graph shows the selected skills organized by module, technology, source, and license, while the ~4,000 candidate skills stay in the vault but **hidden** from Obsidian's graph, search, and link suggestions.

The same relationships must be stored in `registry.db` so agents can query them later. Obsidian is the human view; the database is the source of truth.

Work in the existing project. Read the current code, `catalog.yaml`, `registry.db`, and any existing `.obsidian/` folder first. Do not rebuild what works.

## Ground Rules
1. **Do not move, rename, or edit anything under `skills/` or `_quarantine/`.** The watcher and sync depend on those paths, and skill folders are replaced on sync.
2. **The generator owns only `map/`.** It may create, update, and delete files there (and nowhere else). Every generated note has `generated: true` in its frontmatter. Never touch hand-written notes in `crews/`, `playbooks/`, `notes/`.
3. **Idempotent and deterministic.** Running the generator twice produces identical output (stable ordering, no timestamps in the body). Remove proxy notes for skills that are no longer `selected`.
4. **Merge, don't overwrite, Obsidian config.** When editing `.obsidian/app.json` and `.obsidian/graph.json`, load the existing JSON, change only the keys needed, and keep the rest. Back up each file first as `<name>.bak`.
5. **No invented relationships.** Every link must come from data (catalog, frontmatter, tags, source metadata) or from an explicit rule below.
6. Keep existing tests passing and add new ones.

---

## Task 1: Target Structure
```
DevCrew-Vault/
├── 00-Home.md                    # generated: links to the 7 module hubs + dashboard
├── skills/                       # unchanged (source of truth, hidden from Obsidian index)
├── _quarantine/                  # unchanged (hidden)
├── map/                          # generated, owned by the generator
│   ├── modules/                  # 7 hub notes
│   ├── skills/                   # one proxy note per SELECTED skill
│   ├── tech/                     # technology notes (PostgreSQL, Next.js, LangGraph, OWASP...)
│   ├── sources/                  # one note per upstream repo
│   ├── licenses/                 # one note per license
│   └── dashboard.md              # coverage and open decisions
├── crews/                        # human layer (templates only)
├── playbooks/                    # human layer (templates only)
└── notes/                        # human layer
```
Create `crews/`, `playbooks/`, and `notes/` if missing, each with a short `README.md` explaining its purpose and a blank template note. Do **not** invent crews or playbooks beyond a clearly labeled `_TEMPLATE.md`.

## Task 2: Data Model (extend `registry.db`)
Add, via a migration that is safe to re-run:
- `tech_tags(slug, tag)`: technology tags per skill.
- `skill_links(src_slug, dst_slug, relation, reason, created_by)`: typed links, `relation` in `complements | alternate-of | precedes`.
- Keep the existing `skill_modules` table; use `status = 'selected'` as the definition of "in the map".

**Technology tags.** Add a `tech_keywords` section to `catalog.yaml` (tag name to keyword list, for example `PostgreSQL: [postgres, postgresql, pgvector]`, `Next.js: [next.js, nextjs, app router]`, `LangGraph: [langgraph]`, `OWASP: [owasp]`, `Docker`, `Kubernetes`, `Terraform`, `React`, `Tailwind`, `Playwright`, `RAG`, `Prisma`, `Supabase`, `Firebase`, `GitHub Actions`, and more as the selected skills warrant). Tag a skill when a keyword appears in its slug, description, or frontmatter. Keep to at most 5 tags per skill (highest keyword score first). Only tags used by at least 2 selected skills become tech notes.

## Task 3: Generator (`tools/build_map.py`)
CLI: `python tools/build_map.py [--dry-run] [--clean] [--check]`.
- `--dry-run`: print what would change.
- `--clean`: remove all generated files in `map/` and `00-Home.md` (only files with `generated: true`).
- `--check`: exit non-zero if the map is out of date or invalid (for CI/tests).

Note formats (filenames must be unique and human-readable, because Obsidian links by filename):

**Skill proxy** `map/skills/<slug>.md`
```markdown
---
type: skill-proxy
generated: true
slug: <slug>
module: <module id>
slot: <slot number or null>
source: <source name>
license: <license>
status: selected
skill_path: skills/<slug>/SKILL.md
---
# <slug>
<one-line description from the skill's frontmatter>

**Module:** [[Module N - <name>]]  
**Source:** [[src-<source>]]  
**License:** [[lic-<license>]]  
**Tech:** [[<tag>]], [[<tag>]]

## Related
- Complements: [[<slug>]], ...
- Alternate of: [[<slug>]]
- Comes before: [[<slug>]]

Real skill file: `skills/<slug>/SKILL.md`
```
**Module hub** `map/modules/Module N - <name>.md`: target count, selected count, list of selected skills as links, list of `unfilled` slots (plain text, not links).
**Tech note** `map/tech/<tag>.md`: links to every selected skill with that tag, grouped by module.
**Source note** `map/sources/src-<source>.md`: repo URL, license, commit SHA, links to its selected skills.
**License note** `map/licenses/lic-<license>.md`: links to selected skills under it, and a short plain-language note on obligations (attribution, share-alike) where relevant.
**Home** `00-Home.md`: links to the 7 module hubs, the dashboard, and the human-layer READMEs.
**Dashboard** `map/dashboard.md`: a static Markdown table (generated, works without plugins) of per-module `selected/target`, unfilled slots, skills per license, and skills awaiting a license decision. If the Dataview plugin is installed, you may add an optional extra block, but the static table is required.

Links to the real skill file must be a **code-formatted path**, not a wikilink (the skill folders are excluded from Obsidian's index; see Task 5).

## Task 4: Typed Relations (automatic, capped)
Derive `skill_links` only by these rules, and store the rule name in `reason`:
1. **complements:** two selected skills in **different modules** that share at least one tech tag. Rank pairs by number of shared tags, and keep at most **4** outgoing `complements` links per skill.
2. **alternate-of:** two selected skills in the **same module** that share at least 2 tech tags and have a name or description similarity above a threshold you choose and document (for example the two Tailwind skills). At most 2 per skill.
3. **precedes:** only from an explicit, hand-maintained `catalog.yaml` section `precedes: [[a, b], ...]` (starting empty). Never infer this one.
Make every relation symmetric where it makes sense (`complements`, `alternate-of`) and avoid self-links and duplicates. Print a summary: counts per relation type and the skills with zero links.

## Task 5: Hide the Candidates and Style the Graph (Obsidian config)
1. In `.obsidian/app.json`, add to `userIgnoreFilters`: `skills/`, `_quarantine/`, `.staging/`. This hides candidates and selected skill folders from the graph, search, and quick switcher without moving files.
2. **Test the assumption** that wikilinks and code paths in `map/` still behave sensibly with those folders excluded. If any link to an excluded file shows as unresolved in the graph, confirm that the proxies use only code-formatted paths for `skills/...` (as specified) and report what you observed.
3. In `.obsidian/graph.json`, merge `colorGroups` by path: `map/modules` , `map/skills`, `map/tech`, `map/sources`, `map/licenses`, `crews`, `playbooks`. Pick distinct colors. Set `showOrphans` to `false` and `showAttachments` to `false`.
4. Add `.obsidian/` to the watcher's ignore list if it is not there already.

## Task 6: Keep the Map in Sync
- Add `python tools/watcher.py map` (runs the generator).
- Make the watcher run the generator (debounced, a few seconds) whenever `skill_modules` or the relevant `skills` rows change, so selecting or replacing a skill updates the map automatically.
- The generator must only read from `registry.db` and `catalog.yaml`, never from the raw skill folders directly (except the frontmatter description already stored in the DB).

## Task 7: Agent-Facing Queries (cheap, optional to use)
Add CLI commands so agents can use the relationships without Obsidian:
- `python tools/watcher.py related <slug>` prints linked skills with relation and reason.
- `python tools/watcher.py tech <tag>` prints selected skills with that tag.
Also document the equivalent SQL for `skill_links` and `tech_tags` in the README. Do not add any agent integration beyond this.

## Task 8: Tests and Verification
Add `pytest` tests (using a small fixture database, no network) for:
- Proxy note content for a sample skill, including all frontmatter fields.
- Only `selected` skills get proxies; a skill that leaves `selected` has its proxy removed on the next run.
- Idempotence: running the generator twice yields byte-identical files.
- The generator never writes outside `map/` and `00-Home.md`, and never touches files without `generated: true`.
- Relation rules: caps respected, no self-links or duplicates, `precedes` only from the explicit list.
- Link integrity: every `[[wikilink]]` in `map/` resolves to a generated note (no dangling links), and no proxy is an orphan.
- `.obsidian/app.json` and `graph.json` merging preserves unrelated existing keys.

README steps to add:
1. `python tools/build_map.py --dry-run`, then run it for real
2. `python tools/build_map.py --check`
3. Open `DevCrew-Vault/` in Obsidian (restart it once so the excluded folders take effect), open `00-Home`, then the graph view
4. `python tools/watcher.py related api-design-principles`

## Task 9: Report
Write `MAP-REPORT.md` with real numbers taken from the database and the generated files:
- Number of notes generated per folder, and the total number of nodes and links in the map
- Skills per tech tag, and the tags that were dropped (fewer than 2 skills)
- Relation counts per type, and any selected skill with zero links
- Whether any dangling links or orphan proxies exist (the target is zero)
- What the graph should look like with orphans off, and what was excluded
- Any assumptions that did not hold (for example, how Obsidian treated excluded folders)

## Deliverables Checklist
- [ ] `map/` folder, `00-Home.md`, and the human-layer folders with templates
- [ ] DB migration (`tech_tags`, `skill_links`) and `tech_keywords` in `catalog.yaml`
- [ ] `tools/build_map.py` with `--dry-run`, `--clean`, `--check`
- [ ] Candidates, quarantine, and staging hidden through `.obsidian/app.json`; graph colors set
- [ ] Watcher integration and the `related` / `tech` CLI commands
- [ ] Tests passing, including link-integrity and idempotence
- [ ] `MAP-REPORT.md` and README updates
