# DevCrew AI — `mcp_servers.json` Configuration Specification

## 1. Overview
`mcp_servers.json` defines the runtime MCP server connectivity and tool execution policies for DevCrew AI agents. It serves as a contract between the static catalog/vault and the runtime orchestrator (LangGraph state machines, human approval interrupts, and Docker sandbox).

## 2. Core Safety Guarantees
1. **Approval Authority:** Only servers explicitly pinned in `DevCrew-Vault/catalog.yaml` under `approvals:` may appear in this file. Unapproved servers are strictly excluded.
2. **Version Pinning:** Every server is pinned to an exact semver release. Unpinned downloads (`latest`) are strictly forbidden.
3. **Secret Parameterization:** Environment variables and HTTP headers contain only `${VAR}` placeholders. Literal secrets are prohibited.
4. **Workspace Boundary:** The `workspaceRoot` defines the exact sandbox directory. The filesystem and git servers are scoped strictly to this directory and cannot reference forbidden roots (`d:/UPS_project`, `DevCrew-Vault`).
5. **Tool Execution Policies:** Every server specifies a `toolPolicy`. Write tools are never placed in `allow`; they require human confirmation gates (LangGraph interrupts).

## 3. Schema Reference (`schemas/mcp_servers.schema.json`)

### Root Object
- `schemaVersion` (integer): Version of the schema specification (currently `1`).
- `crew` (string): Crew or agent team identifier (default: `devcrew`).
- `generatedFrom` (object): Provenance metadata:
  - `catalogSha256` (string): Hex SHA-256 hash of `catalog.yaml`.
  - `registrySnapshot` (string): ISO timestamp of the source registry snapshot.
- `workspaceRoot` (string): Bounded target folder for agent modifications (e.g. `d:/UPS_workspace`).
- `servers` (object): Map of server slug to server configuration.

### Server Object
- `registryName` (string): Official MCP registry reverse-DNS package name.
- `version` (string): Exact semver version string.
- `transport` (string): `stdio`, `streamable-http`, or `sse`.
- `command` (string): Command to execute (`npx`, `uvx`, `docker`, `python`) for stdio servers.
- `args` (array of strings): Command arguments, including exact version specifiers and workspace bounds.
- `url` (string, optional): Remote endpoint URL for streamable-http servers.
- `headers` (object, optional): HTTP headers with `${VAR}` placeholders.
- `env` (object): Environment variable mappings (`${VAR}`).
- `capability` (string): `read-only`, `read-write`, `destructive`, or `unknown-treat-as-write`.
- `toolPolicy` (object):
  - `default`: Default action (`require-approval`, `allow`, `deny`).
  - `allow`: List of tool names that execute without human confirmation.
  - `requireApproval`: List of tool names that pause for human approval before execution.
- `timeoutSeconds` (integer): Execution timeout threshold (5–600 seconds).
- `enabled` (boolean): Whether the server is active.
- `pairedSkills` (array of strings, optional): Slugs of paired skills teaching API usage for this server.

## 4. Per-Server Policy Reference

### 1. `filesystem` (`io.github.modelcontextprotocol/filesystem@2.2.0`)
- **Transport:** `stdio` (`npx -y @modelcontextprotocol/server-filesystem@2.2.0 <workspaceRoot>`)
- **Capability:** `read-write`
- **Allowed Tools:** `read_text_file`, `list_directory`, `read_media_file`, `get_file_info`
- **Requires Approval:** `write_file`, `edit_file`, `move_file`, `create_directory`
- **Bound:** Scoped strictly to `workspaceRoot`.

### 2. `git` (`io.github.modelcontextprotocol/git@0.6.2`)
- **Transport:** `stdio` (`uvx mcp-server-git==0.6.2 --repository <workspaceRoot>`)
- **Capability:** `read-write`
- **Allowed Tools:** `git_status`, `git_diff`, `git_log`, `git_show`
- **Requires Approval:** `git_commit`, `git_add`, `git_reset`, `git_create_branch`, `git_checkout`, `git_push`
- **Push Policy:** Push tools are disabled by default unless `allowPush: true` is configured.

### 3. `playwright-mcp` (`io.github.microsoft/playwright-mcp@0.0.84`)
- **Transport:** `stdio` (`npx -y @playwright/mcp@0.0.84`)
- **Capability:** `read-write`
- **Allowed Tools:** `browser_screenshot`, `browser_get_html`, `browser_evaluate`
- **Requires Approval:** `browser_navigate`, `browser_click`, `browser_fill`, `browser_hover`, `browser_press_key`, `browser_select_option`
- **Untrusted Content:** Web content retrieved via Playwright is untrusted text. Mutating tools triggered following navigation require human approval.

### 4. `context7` (`io.github.upstash/context7@4.5.1`)
- **Transport:** `stdio` (`npx -y @upstash/context7-mcp@4.5.1`)
- **Capability:** `read-only`
- **Required Secret:** `${CONTEXT7_API_KEY}`
- **Fallback:** If `${CONTEXT7_API_KEY}` is missing from the environment, `enabled` is set to `false`.

## 5. Client Exports
In addition to the primary `mcp_servers.json` format, DevCrew generates exports for standard MCP hosts:
- `DevCrew-Vault/mcp/configs/devcrew/exports/claude-desktop.json`
- `DevCrew-Vault/mcp/configs/devcrew/exports/cursor.json`
Both exports parameterize secrets and carry the header comment `_generated: "Review before copying into your client config"`.
