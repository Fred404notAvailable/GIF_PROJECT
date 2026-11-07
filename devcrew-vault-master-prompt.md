# Master Prompt: DevCrew AI Skill Vault (Ingest, Validate, Watch, Index)

## Role
You are a senior platform engineer building the local-first **DevCrew Vault**: a folder of `agentskills.io`-style skills (plain-text `SKILL.md` packages), populated from real open-source registries, validated against the spec, and indexed into a database in real time by a background file watcher.

## Guiding Principles
1. **Real over synthetic.** Ingest battle-tested community skills. Do not invent filler content. Hand-authored skills are a last resort (see Phase 4) and must be clearly labeled as such.
2. **Local-first.** Everything runs offline after the initial sync. No cloud service is required to read or index the vault.
3. **Idempotent and safe.** Every script can be re-run without duplicating or corrupting data. Never execute code found inside ingested skills.
4. **Provenance and licensing are mandatory.** Every ingested skill records where it came from, at which commit, and under what license.
5. **Cross-platform.** Must work on Windows, macOS and Linux (use `pathlib`, avoid shell-specific commands).

## Tech Stack (default, override only with justification)
- Python 3.11+, `watchdog`, `PyYAML`, `sqlite3` (stdlib, WAL mode, FTS5), `pytest`
- Git CLI for cloning (fallback: GitHub zip download via HTTPS)
- Single config file: `devcrew.config.yaml` (no hard-coded paths or URLs in code)

## Target Layout
```
devcrew-vault-project/
├── devcrew.config.yaml          # sources, paths, allowed licenses, DB path
├── requirements.txt
├── README.md
├── DevCrew-Vault/
│   ├── skills/
│   │   └── <skill-slug>/
│   │       ├── SKILL.md         # required
│   │       ├── scripts/         # optional
│   │       ├── references/      # optional
│   │       ├── assets/          # optional
│   │       ├── LICENSE*         # preserved from upstream if present
│   │       └── .source.json     # provenance (added by sync)
│   ├── _quarantine/             # skills that failed validation
│   └── registry.db              # SQLite index
├── tools/
│   ├── scaffold.py              # Phase 1
│   ├── sync_skills.py           # Phase 2
│   ├── validate_skills.py       # Phase 3
│   └── watcher.py               # Phase 5
├── tests/
└── .staging/                    # temp clones (gitignored)
```

---

## Phase 1: Vault Scaffold
1. Write `tools/scaffold.py` to create `DevCrew-Vault/skills/`, `_quarantine/`, and `.staging/` if missing. It must be safe to re-run and must never overwrite existing files.
2. Support an optional `--categories` flag that creates empty, well-documented category skeleton folders (backend architecture, security auditing, frontend frameworks, AI orchestration, DevOps, testing, data) **only** as placeholders. Each placeholder gets a one-line `README.md`, not a fake `SKILL.md`.
3. Provide `--dry-run` that prints what would be created.

## Phase 2: Source Sync (Fetch Real Skills)
Write `tools/sync_skills.py` driven by `devcrew.config.yaml`:

```yaml
sources:
  - name: anthropic-skills
    url: https://github.com/anthropics/skills.git
    ref: main
    skills_glob: "skills/*/SKILL.md"
  # Add further agentskills.io-compatible repositories here.
allowed_licenses: [MIT, Apache-2.0, BSD-3-Clause, CC-BY-4.0]
on_unknown_license: quarantine   # quarantine | skip | allow
on_slug_collision: namespace     # namespace | skip | overwrite
```

Requirements:
1. Shallow-clone (`--depth 1`) each source into `.staging/<source-name>/`; if the clone already exists, `git fetch` and fast-forward instead of re-cloning.
2. Discover skills by locating every `SKILL.md`; treat its parent folder as the skill package. Copy the **entire folder** (including `scripts/`, `references/`, `assets/`, license files) into `DevCrew-Vault/skills/<slug>/`.
3. Write `.source.json` into each skill: `{source_name, repo_url, ref, commit_sha, upstream_path, license, synced_at, content_sha256}`.
4. **License gate:** read the skill's own `LICENSE*` (falling back to the repo license). Apply `allowed_licenses` and `on_unknown_license`. Note that some upstream skills are source-available rather than open source; these must be flagged, never silently copied.
5. **Collision handling:** if two sources provide the same slug, namespace the later one (`<source>--<slug>`) and log it.
6. **Incremental updates:** skip skills whose `content_sha256` is unchanged; on change, replace the folder atomically (copy to temp dir, then rename). Never delete locally authored skills.
7. Flags: `--source <name>`, `--dry-run`, `--force`, `--prune` (remove skills that vanished upstream, with confirmation).
8. Print a summary table: added / updated / unchanged / skipped / quarantined, per source.
9. Network failures for one source must not abort the others.

## Phase 3: Metadata Normalization & Spec Validation
Write `tools/validate_skills.py` (also importable as a module, because the watcher reuses it).

For each skill folder, check:
- **Frontmatter present:** file begins with `---`, valid YAML, closed by `---`.
- **`name`:** required; 1-64 chars; lowercase letters, digits and hyphens only; no leading, trailing or consecutive hyphens; **must equal the folder name**.
- **`description`:** required; non-empty; max 1024 chars; must say both *what the skill does* and *when to use it* (warn if it lacks trigger language).
- **Optional fields** (`license`, `compatibility`, `metadata`, `allowed-tools`): validate types if present; preserve unknown keys.
- **Body:** non-empty Markdown; warn if it is very long (suggest moving detail to `references/`).
- **Referenced files:** relative links to `scripts/`, `references/`, `assets/` must resolve.
- **Safety scan (static only, never execute):** flag suspicious patterns in `scripts/` (e.g. `curl | sh`, `rm -rf /`, base64-decoded execution, credential exfiltration) and flag prompt-injection phrases in `SKILL.md`.

Normalization (only with `--fix`, and always report each change):
- Lowercase and slugify `name`; trim whitespace in `description`.
- Normalize line endings to LF and ensure a trailing newline.
- Add `license:` frontmatter from `.source.json` when missing.

Outcomes: `valid`, `valid-with-warnings`, or `invalid`. Invalid skills are moved to `_quarantine/<slug>/` together with a `REPORT.md` listing each failure. Emit a machine-readable `validation-report.json` and a human-readable summary.

## Phase 4: The Four Reference Skills (Real First, Authored Last)
Target skills: `dotnet-clean-architecture`, `owasp-top10-auditor`, `nextjs-app-router-rsc`, `langgraph-cyclic-state-machine`.

1. Search the configured sources for an existing equivalent of each. If found, ingest it through the normal Phase 2 pipeline.
2. Only for those with no real upstream match, generate a production-grade `SKILL.md` and mark it clearly:
   - frontmatter `metadata: { origin: authored, review_status: needs-human-review }`
   - folder lives in `DevCrew-Vault/skills/` but `.source.json` has `source_name: local-authored`
3. Each authored skill needs: a trigger-rich `description`, a "When to use / When not to use" section, numbered procedure, concrete checklists, common pitfalls, and at least one worked example. Include a `references/` file for deep detail rather than bloating `SKILL.md`.
4. Report which of the four were ingested versus authored.

## Phase 5: Real-Time File Watcher and Registry
Write `tools/watcher.py` using `watchdog`.

**Database schema (SQLite, WAL mode):**
```sql
skills(
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  body TEXT NOT NULL,
  frontmatter_json TEXT NOT NULL,
  license TEXT,
  source_name TEXT,
  commit_sha TEXT,
  path TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  validation_status TEXT NOT NULL,       -- valid | warnings | invalid
  validation_messages TEXT,
  has_scripts INTEGER, has_references INTEGER, has_assets INTEGER,
  created_at TEXT, updated_at TEXT
);
CREATE VIRTUAL TABLE skills_fts USING fts5(name, description, body, content='skills', content_rowid='id');
```
Keep the FTS table in sync with triggers.

**Behavior:**
1. **Initial reconciliation on startup:** full scan of the vault, upsert everything, and remove DB rows whose files no longer exist.
2. **Event handling:** `created`, `modified`, `deleted`, and `moved` for any file inside a skill folder. Changes to `scripts/`, `references/` or `assets/` update the parent skill's flags and hash. Resolve the owning skill from the path.
3. **Debounce** events (~500 ms per skill) to handle editors that write files multiple times, and ignore temp, swap and hidden files (`.swp`, `~`, `.DS_Store`).
4. **Skip no-op writes** by comparing `content_sha256`.
5. **Invalid files do not crash the watcher.** Record them with `validation_status = invalid` and the error messages; keep the last good version's data available.
6. **Graceful shutdown** (SIGINT/SIGTERM) and structured logging (timestamp, event, slug, result).
7. **No restart required** for any change. Reload `devcrew.config.yaml` on change as a bonus.
8. Provide a small CLI: `python tools/watcher.py run`, `... scan` (one-shot reindex), `... search "<query>"` (FTS5 query), `... list`, `... show <slug>`.

---

## Testing and Verification
Provide `pytest` tests covering:
- Validator: valid skill, missing `name`, name/folder mismatch, oversize description, bad YAML, broken relative link.
- Sync: collision namespacing, unchanged-skip via hash, license gate (use a local fixture repo, not the network).
- Watcher: create, edit, rename, delete, rapid repeated saves (debounce), invalid edit then fix.

Provide a README with copy-paste verification steps for each OS:
1. Create venv and `pip install -r requirements.txt`
2. `python tools/scaffold.py`
3. `python tools/sync_skills.py --dry-run`, then run for real
4. `python tools/validate_skills.py --report`
5. Start the watcher in one terminal; in another, create, edit and delete a `SKILL.md`, and show the registry updating via `python tools/watcher.py list` and `sqlite3 DevCrew-Vault/registry.db "SELECT slug, validation_status FROM skills;"`
6. Run `pytest`

## Code Quality Requirements
- Modular code: separate modules for config, git operations, parsing, validation, database and watcher; type hints throughout; docstrings on public functions.
- Clear errors, no silent failures, and non-zero exit codes on failure.
- Pin dependencies in `requirements.txt`; add `.gitignore` for `.staging/` and `registry.db`.
- Do not hard-code secrets; never execute ingested scripts.

## Deliverables Checklist
- [ ] Scaffolded vault and config file
- [ ] Working sync script with provenance and license gating
- [ ] Validator with quarantine and `--fix`
- [ ] Four target skills (ingested where possible; authored ones flagged)
- [ ] Watcher with SQLite registry, FTS5 search and CLI
- [ ] Tests passing and README with verification steps
- [ ] Final summary: skills ingested per source, quarantined (with reasons), skills authored, and known limitations
