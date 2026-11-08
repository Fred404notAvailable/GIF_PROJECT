# DevCrew AI Skill Vault

A local-first, real-time-indexed vault of open-source AI agent skills organized into 7 professional modules.

---

## Overview

The DevCrew Vault ingests, validates, classifies, and indexes [SKILL.md](https://agentskills.io)-format skill packages from verified open-source repositories. Skills are organized into 7 modules covering the full modern engineering stack, with a target of **100 curated skills**.

| # | Module | Target |
|---|--------|--------|
| 1 | Modern Backend & API Development | 15 |
| 2 | Frontend & UI Engine Frameworks | 15 |
| 3 | Database, Vector & Storage Management | 15 |
| 4 | Security, Auditing & SecOps | 15 |
| 5 | AI Architecture, LLM & Prompt Engineering | 15 |
| 6 | Testing, QA & Reliability Engineering | 10 |
| 7 | DevOps, Containers & Cloud Automation | 15 |

---

## Quick Start

### 1. Set up environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Scaffold the vault

```bash
python tools/scaffold.py
```

### 3. Sync skills from upstream repos (dry run first)

```bash
python tools/sync_skills.py --dry-run
python tools/sync_skills.py
```

### 4. Validate all skills

```bash
python tools/validate_skills.py --report
```

Produces `validation-report.json` and prints a human-readable summary. Invalid skills are quarantined to `DevCrew-Vault/_quarantine/`.

Apply safe normalizations:

```bash
python tools/validate_skills.py --fix --report
```

### 5. Check module coverage

```bash
python tools/sync_skills.py --coverage
```

Writes `coverage-report.md` showing `selected/target` per module with shortfalls clearly marked.

### 6. Start the real-time watcher

In one terminal:

```bash
python tools/watcher.py run
```

In another terminal, verify the registry is updating:

```bash
# List all indexed skills
python tools/watcher.py list

# FTS5 search
python tools/watcher.py search "terraform kubernetes"

# Show one skill's details
python tools/watcher.py show terraform-skill

# View module breakdown
python tools/watcher.py modules

# View skills in a specific module
python tools/watcher.py module 7
```

### 7. Obsidian Map Layer & Graph View

Generate the structured knowledge graph connecting selected skills across modules, technologies, sources, and licenses:

```bash
# 1. Preview changes
python tools/build_map.py --dry-run

# 2. Build map notes & configure Obsidian
python tools/build_map.py

# 3. Verify graph integrity and link resolution
python tools/build_map.py --check
```

Then open `DevCrew-Vault/` in Obsidian:
- Restart Obsidian once if open so `.obsidian/app.json` ignore filters take effect (hiding ~4,000 raw candidate & quarantine folders from graph/search).
- Open `00-Home.md` as your root navigation dashboard.
- Press `Ctrl+G` (or `Cmd+G` on macOS) to open the graph view:
  - **Module Hubs:** Purple
  - **Skill Proxies:** Blue
  - **Tech Clusters:** Emerald
  - **Sources:** Amber
  - **Licenses:** Red
  - **Crews / Playbooks:** Cyan / Pink

### 8. Headless Agent CLI Queries

Agents can query technology clusters and typed relations directly without running Obsidian:

```bash
# Show typed relationships for a skill (complements, alternate-of, precedes)
python tools/watcher.py related api-design-principles

# Show all selected skills tagged with a technology
python tools/watcher.py tech PostgreSQL
```

### 9. MCP Server Catalog Workflow (Ingest, Vet, Approve, Configure)

The DevCrew Vault extends beyond static skills to curated live **Model Context Protocol (MCP)** servers, connecting live tool capabilities with the skills that teach them:

```bash
# 1. Preview and sync real servers from official registry and reference implementations
python tools/mcp_sync.py --dry-run
python tools/mcp_sync.py

# 2. Perform static security vetting, scoring, module assignment, and skill pairing
python tools/mcp_vet.py

# 3. Review candidate servers awaiting human decision
# Open MCP-APPROVALS-NEEDED.md, review candidate versions, and add desired approvals
# to DevCrew-Vault/catalog.yaml under `approvals: {<name>: <version>}`, then re-sync:
python tools/mcp_sync.py
python tools/mcp_vet.py

# 4. Generate client configuration examples with pinned versions and secret placeholders
python tools/mcp_config.py --crew backend

# 5. Check and regenerate map layer with MCP nodes and pairs-with links
python tools/build_map.py --check

# 6. Run test suite
pytest
```

#### Headless MCP CLI Queries

```bash
# List all ingested MCP servers with scores and capability classes
python tools/watcher.py mcp-list

# Show full details and vetting breakdown for a single MCP server
python tools/watcher.py mcp-show modelcontextprotocol-fetch-mcp

# Full-text search over MCP server titles, names, and descriptions
python tools/watcher.py mcp-search "database postgres"

# Find MCP servers that pair with a specific skill
python tools/watcher.py mcp-pairs angular-best-practices
```

### 10. Query the SQLite registry directly


```bash
sqlite3 DevCrew-Vault/registry.db "SELECT slug, validation_status FROM skills;"
sqlite3 DevCrew-Vault/registry.db "SELECT module_id, status, COUNT(*) FROM skill_modules GROUP BY 1,2;"
```

### 10. Run tests

```bash
pytest
```

---

## Tools Reference

| Script | Purpose |
|--------|---------|
| `tools/scaffold.py` | Create vault directory layout (idempotent) |
| `tools/sync_skills.py` | Clone/fetch sources and copy skills into vault |
| `tools/validate_skills.py` | Validate SKILL.md packages; quarantine invalid |
| `tools/watcher.py` | Real-time file watcher + SQLite FTS5 registry |
| `tools/build_map.py` | Obsidian map layer generator (modules, tech, proxies) |
| `tools/verify_vault.py` | Vault consistency gate (checks license, disk, status) |
| `tools/catalog.py` | Module classification, ranking, dedup, coverage |
| `tools/config.py` | Load `devcrew.config.yaml` |
| `tools/parsing.py` | Parse SKILL.md frontmatter, compute SHA-256 |
| `tools/db.py` | SQLite schema, upsert/delete, FTS5 search |
| `tools/git_ops.py` | Git clone, sparse checkout, zip fallback |

---

## Module Classification

Skills are automatically classified into modules by keyword scoring. The classifier:
- Scores each skill against each module's keyword list
- Awards bonus points for vendor-published sources
- Respects manual override entries in `catalog.yaml`

The `catalog.yaml` file contains:
- Module metadata and keyword lists
- 100 pinned slot assignments (one slot per target skill)
- Alternate skill lists per module
- Manual override map (`slug → module_id`)

---

## License Gating

| License | Policy |
|---------|--------|
| MIT, Apache-2.0, BSD-3-Clause, CC-BY-4.0 | ✅ Allowed |
| CC-BY-SA-4.0 (Trail of Bits, netresearch) | ⚠️ Needs explicit user approval |
| UNKNOWN / no license | ❌ Quarantined |

> **Important:** Trail of Bits skills (slots 50–58) are CC-BY-SA-4.0 (share-alike). These are not in `allowed_licenses` by default. Add `CC-BY-SA-4.0` to `allowed_licenses` in `devcrew.config.yaml` only after reviewing the share-alike requirements.

---

## MCP Server Configuration & Safe Loader

DevCrew AI generates and enforces schema-validated MCP configurations for agent runtimes (LangGraph state machines, human approval gates, Docker sandboxes).

### Approved Servers (catalog.yaml)
1. `io.github.modelcontextprotocol/filesystem` (`2.2.0`): Local filesystem operations scoped strictly to `d:/UPS_workspace`. Mutating tools (`write_file`, `edit_file`, etc.) require explicit human approval.
2. `io.github.modelcontextprotocol/git` (`0.6.2`): Local git operations scoped to `d:/UPS_workspace`. Mutating tools (`git_commit`, `git_push`, `git_reset`, etc.) require human approval.
3. `io.github.microsoft/playwright-mcp` (`0.0.84`): Local browser automation for E2E testing. Navigation is gated by human approval; web page text is untrusted.
4. `io.github.upstash/context7` (`4.5.1`): Read-only documentation and context retriever. Requires `${CONTEXT7_API_KEY}`.

### Quick Start: Generate and Load MCP Configurations

1. **Configure Environment Secrets (Optional):**
   Create a `.env.mcp` file in the project root with your Upstash Context7 API key (or leave it unset to keep Context7 disabled without failing the whole configuration):
   ```bash
   # .env.mcp (git-ignored)
   CONTEXT7_API_KEY="your_api_key_here"
   ```

2. **Preview Configuration (Dry-Run):**
   ```bash
   python tools/mcp_config.py --crew devcrew --dry-run
   ```

3. **Generate Configuration and Host Exports:**
   ```bash
   python tools/mcp_config.py --crew devcrew
   ```
   Generates:
   - `DevCrew-Vault/mcp/configs/devcrew/mcp_servers.json` (DevCrew schema-validated runtime config)
   - `DevCrew-Vault/mcp/configs/devcrew/exports/claude-desktop.json` (Claude Desktop format)
   - `DevCrew-Vault/mcp/configs/devcrew/exports/cursor.json` (Cursor IDE format)

4. **Verify Consistency & Drift Check:**
   ```bash
   python tools/mcp_config.py --crew devcrew --check
   ```

5. **Validate with Runtime Safe Loader:**
   ```bash
   python tools/mcp_loader.py --crew devcrew --validate
   ```

---

## Layout

```
UPS_project/
├── devcrew.config.yaml          # Sources, paths, allowed licenses, DB path
├── requirements.txt
├── README.md
├── catalog.yaml → DevCrew-Vault/catalog.yaml
├── coverage-report.md           # Generated by --coverage
├── DevCrew-Vault/
│   ├── skills/
│   │   └── <skill-slug>/
│   │       ├── SKILL.md
│   │       ├── scripts/         # Optional
│   │       ├── references/      # Optional
│   │       ├── assets/          # Optional
│   │       └── .source.json     # Provenance (source, commit, license, SHA-256)
│   ├── _quarantine/             # Failed validation or license gate
│   ├── catalog.yaml             # Module catalog with pinned slots
│   └── registry.db              # SQLite (FTS5) index
├── tools/
│   ├── scaffold.py
│   ├── sync_skills.py
│   ├── validate_skills.py
│   ├── watcher.py
│   ├── catalog.py
│   ├── config.py
│   ├── parsing.py
│   ├── db.py
│   └── git_ops.py
├── tests/
│   ├── conftest.py
│   ├── test_validator.py
│   ├── test_classify.py
│   ├── test_ranking.py
│   ├── test_coverage.py
│   └── test_skill_modules_sync.py
└── .staging/                    # Temp git clones (gitignored)
```

---

## Obsidian

Open `DevCrew-Vault/` as an Obsidian vault for a visual knowledge graph of all skills. `.obsidian` is in the watcher's ignore list so Obsidian config changes don't trigger re-indexing.

---

## Notes

- **Never execute ingested scripts.** The safety scanner (`validate_skills.py`) flags dangerous patterns but never runs them.
- **Idempotent.** All scripts can be re-run safely. Skills are only re-copied when their `content_sha256` changes.
- **Local-first.** After the initial sync, everything works offline.
- **Windows support.** `pathlib` is used throughout; no shell-specific commands.
