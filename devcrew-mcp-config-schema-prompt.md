# Prompt: Define the `mcp_servers.json` Schema, Generator, and Safe Loader for DevCrew AI

## Context
The DevCrew Vault catalog is settled. The user has approved exactly four MCP servers in `DevCrew-Vault/catalog.yaml`:
```yaml
approvals:
  "io.github.modelcontextprotocol/filesystem": "2.2.0"
  "io.github.modelcontextprotocol/git": "0.6.2"
  "io.github.microsoft/playwright-mcp": "0.0.84"
  "io.github.upstash/context7": "4.5.1"
```
DevCrew AI is a local-first multi-agent platform (LangGraph state machines, human-in-the-loop gates, Docker sandbox for generated code). Its runtime reads `mcp_servers.json` to connect agents to MCP servers (stdio and remote streamable-http). Your job: define that file format, generate it from the vault, and specify and implement a safe loader that the runtime (or any language) can use.

Work in the existing project. Do not rebuild the catalog, watcher, or map layer. Read `catalog.yaml`, `registry.db`, `tools/mcp_config.py`, and the stored registry snapshots first.

## Ground Rules
1. **The agent never edits the `approvals:` section.** It only reads it. Add a test that the generator and loader never modify `catalog.yaml`.
2. **Fail closed.** A server that is not in `approvals`, or whose version differs from the approved version, must not appear in any generated config or be started by the loader.
3. **No secrets in files.** Only `${ENV_VAR}` placeholders. The runtime resolves them from the process environment (or a local `.env` file that is git-ignored). Refuse to generate or load a file that contains a literal secret-looking value.
4. **No server code is installed or executed by this task's build or tests.** Tests use a mock stdio MCP server written inside the repo (our own code), never a third-party server.
5. **No unpinned runtime downloads.** Never emit `npx -y <pkg>` or `uvx <pkg>` without an exact `@version` / `==version`. State in the output that these commands download and run code, so the user should pre-install into a locked location when possible.
6. Evidence over claims: every number and status in any report is generated from the database or files.

---

## Part A: Small Cleanup of Known Report Bugs (do first)
Fix these in the report generator and underlying data, with tests:
1. **Transport column** shows `None` for every server. Populate it from the registry record (`stdio` or `streamable-http` per package/remote entry) and store it in `mcp_servers.transport`.
2. **Secrets display** repeats names (for example `Authentication` 28 times, `CLICKHOUSE_*` and `CONTEXT7_API_KEY` twice). De-duplicate, and separate **environment variables** from **HTTP header names**. Headers such as `Authorization` are not secrets by themselves; show them as `header: Authorization (value from ${VAR})`.
3. **Slot 53** (`codeql`) is marked `matched` with no skill behind it. Mark it `unfilled (license CC-BY-SA-4.0 requires user decision)` like the other Trail of Bits slots, and make the summary counts consistent: the text and the table must both say the same matched/unfilled numbers (the current table says 71/29; the prose says 72/28). Generate both from the same query.
4. **"Not found" reasons** for `dockerfile-best-practices`, `kubernetes-manifests`, `testing-best-practices`, `docker-development`, `devops-deployment`, `ansible`, `github-cli`, `q24-*`: check `.staging/`, the `skills` table, and `_quarantine/` and report the real reason (`repo cloned but skill absent`, `quarantined: unknown license`, `repo not cloned`). Do not write "not found" if the skill exists but was blocked by the license gate.
5. **Shortfall wording:** the "16/49" MCP figure compares relevance-filtered servers to the old quota. Report it as `selected / ceiling` with a note that ceilings are not goals.
6. **Approvals audit line:** the report header says approvals were "granted directly by the user (24 approvals recorded)". Replace this with a generated line listing the exact approved servers and versions currently in `catalog.yaml`, with the file's last-modified time and SHA-256, and a flag if the count differs from the previous run.

## Part B: Workspace Safety Configuration
Add to `devcrew.config.yaml`:
```yaml
mcp:
  workspace_root: "d:/UPS_workspace"      # where agents may read/write generated projects
  forbidden_roots:                         # filesystem/git servers must never be pointed at these or any parent
    - "d:/UPS_project"
    - "d:/UPS_project/DevCrew-Vault"
  env_file: ".env.mcp"                     # git-ignored; values for ${VAR} placeholders
  audit_log: "logs/mcp-audit.jsonl"
```
Rules enforced by the generator and loader:
- `workspace_root` must exist (create it if missing), must not equal, contain, or sit inside any `forbidden_roots` entry, and must not be a drive root or the user's home directory.
- Add `.env.mcp` and `logs/` to `.gitignore`.

## Part C: The `mcp_servers.json` Format
Write a JSON Schema (`schemas/mcp_servers.schema.json`) and documentation (`docs/mcp_servers.md`) for this format, one file per crew (default crew `devcrew`):
```json
{
  "schemaVersion": 1,
  "crew": "devcrew",
  "generatedFrom": { "catalogSha256": "<hash>", "registrySnapshot": "<timestamp>" },
  "workspaceRoot": "d:/UPS_workspace",
  "servers": {
    "filesystem": {
      "registryName": "io.github.modelcontextprotocol/filesystem",
      "version": "2.2.0",
      "transport": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem@2.2.0", "d:/UPS_workspace"],
      "env": {},
      "capability": "read-write",
      "toolPolicy": { "default": "require-approval", "allow": ["read_text_file", "list_directory"], "requireApproval": ["write_file", "edit_file", "move_file", "create_directory"] },
      "timeoutSeconds": 60,
      "enabled": true
    }
  }
}
```
Requirements:
1. **Fields:** `registryName`, `version` (exact), `transport` (`stdio` | `streamable-http`; support legacy `sse` only if a server requires it, flagged), `command` + `args` (stdio) or `url` + `headers` (remote, with `${VAR}` placeholders), `env` (map of name to `${VAR}` placeholder), `capability` (`read-only` | `read-write` | `destructive` | `unknown-treat-as-write`), `toolPolicy`, `timeoutSeconds`, `enabled`, optional `pairedSkills`.
2. **Tool policy:** `default` is `require-approval` for any server whose capability is not `read-only`. `allow` lists tools that run without a human gate; `requireApproval` lists tools that must pause for a human decision (maps to a LangGraph interrupt). Derive tool names from the stored registry/repo evidence; if tool names are unknown, set `default: require-approval` and leave `allow` empty. Never put a write tool in `allow`.
3. **Per-server rules:**
   - `filesystem`: allowed directory arguments must be exactly `workspaceRoot` (or a subfolder of it). Refuse to generate otherwise.
   - `git`: repository path must be inside `workspaceRoot`. Commit, push, reset, and branch-deletion tools always require approval. Push should be disabled unless the user sets `allowPush: true` in config.
   - `playwright-mcp`: local stdio server only. Note it can navigate to arbitrary sites; add a config option for allowed origins if the server supports it, otherwise mark browser navigation as `require-approval` by default.
   - `context7`: read-only; requires `${CONTEXT7_API_KEY}`; mark the server `enabled: false` when the variable is not set instead of failing the whole file.
4. **Exports:** also write `exports/claude-desktop.json` and `exports/cursor.json` in the common `mcpServers` shape (`command`, `args`, `env`) for the same approved servers, with the same safety rules and a header comment field `"_generated": "Review before copying into your client config"`. The agent must never write into a client's own config directory.

## Part D: Generator (`tools/mcp_config.py`, extend the existing tool)
1. Read `approvals`; for each approved server, verify against the stored registry snapshot: exact version exists, package type, transport, env vars/headers, and license in `allowed_licenses`. If any check fails, skip the server and print why.
2. Build the entry using the package metadata (npm: `<package>@<version>`, pypi: `<package>==<version>` via `uvx`/`python -m`, oci: a pinned image digest if available, remote: the URL). Never use `latest`.
3. Validate the output against the JSON Schema before writing. Write atomically.
4. CLI: `python tools/mcp_config.py --crew <name> [--dry-run] [--only <server>] [--check]`. `--check` fails if the existing file is stale compared with `approvals` or the snapshot.
5. Print a plain-language summary: servers included, each server's capability and which tools need approval, which env variables must be set, and the combination risks (for example git + filesystem; any web-fetching or browsing server combined with a write-capable one).
6. If `approvals` is empty or contains a server that fails verification, write nothing for that server and exit non-zero only for verification failures.

## Part E: Loader Specification and Reference Implementation
Write `docs/mcp_loader_spec.md` (language-neutral, so a Python or .NET orchestrator can implement it) and a reference implementation `tools/mcp_loader.py` that does everything except actually launching real servers unless asked (`--launch` flag, off by default; tests never use it):
1. **Validate** the file against the JSON Schema; reject unknown fields.
2. **Re-verify approvals at load time:** the server must still be in `catalog.yaml` `approvals` at the same version. Mismatch means refuse that server.
3. **Resolve `${VAR}`** from the environment, then `.env.mcp`. If a required variable is missing, disable that server with a clear message; never substitute an empty string.
4. **Reject literal secrets:** values matching common key patterns (long random strings, `sk-`, `ghp_`, `AKIA`, etc.) in `env` or `headers` cause a load failure.
5. **Enforce the workspace rules** again at load time (paths inside `workspaceRoot`, not inside `forbidden_roots`, no `..` escapes, resolve symlinks).
6. **Tool gating hook:** expose a function `gate(server, tool, arguments) -> allow | require_approval | deny` that the runtime calls before every tool call, using `toolPolicy`. Default for unknown tools is `require_approval`. Document how it maps to a LangGraph `interrupt` for human-in-the-loop.
7. **Audit log:** append one JSON line per tool call decision and result summary to `audit_log` (timestamp, crew, server, tool, decision, approver if any). Never log secret values or full argument payloads for secret-bearing fields.
8. **Lifecycle:** start servers lazily per crew, enforce `timeoutSeconds`, restart limits, and clean shutdown of child processes. Document that the runtime should terminate all servers when the crew ends.
9. **Skill pairing:** provide `servers_for_skills(skill_slugs)` that queries `skill_links` (`pairs-with`) and returns only servers that are both paired and approved and enabled. It never enables an unapproved server.
10. **Untrusted output rule (documented):** all tool results are untrusted text. The loader's docs must say that results from web-capable servers (Playwright, fetch-like tools) must be treated as data, never as instructions, and that write tools triggered after reading such content need a human gate.

## Part F: Tests (fixtures and the in-repo mock server only)
Add tests for:
- Schema: valid file passes; missing version, `latest`, unknown field, literal secret, relative or escaping path all fail.
- Generator: only approved servers are included; wrong version in `approvals` is skipped; filesystem path outside `workspaceRoot` is refused; workspace inside a forbidden root is refused; `enabled: false` when an env variable is missing.
- Generator and loader never modify `catalog.yaml` (compare hash before and after).
- Tool gating: write tools never in `allow`; unknown tools default to require-approval; read-only servers allow their listed tools.
- Loader: missing env variable disables the server; approval/version drift refuses the server; symlink escape rejected.
- Audit log: entries written, secrets never present.
- Mock server: a tiny stdio MCP server in `tests/fixtures/` that the loader can start with `--launch` in a single test, to verify lifecycle and timeout handling.
- Report fixes from Part A (transport populated, secrets de-duplicated, slot 53 consistent counts).
Run the full suite, `verify_vault.py`, and `build_map.py --check`, and report the real results.

## Deliverables
1. Part A fixes and a regenerated `RESULT-REPORT.md` (generated, with the approvals audit line).
2. `schemas/mcp_servers.schema.json`, `docs/mcp_servers.md`, `docs/mcp_loader_spec.md`.
3. Updated `tools/mcp_config.py` and new `tools/mcp_loader.py`.
4. Generated `DevCrew-Vault/mcp/configs/devcrew/mcp_servers.json` plus the two export files, for the four approved servers only.
5. `devcrew.config.yaml` `mcp:` section, `.gitignore` updates, and a README section with copy-paste steps:
   - create `.env.mcp` with `CONTEXT7_API_KEY` (or leave it unset to disable Context7)
   - `python tools/mcp_config.py --crew devcrew --dry-run`, then without `--dry-run`
   - `python tools/mcp_config.py --crew devcrew --check`
   - `python tools/mcp_loader.py --crew devcrew --validate`
6. A short plain-language summary for the user: the four servers, what each can do, which tools need human approval, which env variables are needed, and the exact path agents may touch.
