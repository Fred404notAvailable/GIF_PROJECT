# DevCrew AI — Safe MCP Loader Specification

## 1. Scope & Purpose
This document provides a language-neutral specification for loading, verifying, gating, and managing Model Context Protocol (MCP) servers in DevCrew AI. Implementations (such as the reference Python implementation `tools/mcp_loader.py` or a compiled .NET runtime orchestrator) must adhere strictly to these validation and execution invariants.

---

## 2. Invariants & Security Principles

1. **Fail-Closed Verification:** A server is never activated unless:
   - It is explicitly listed in `DevCrew-Vault/catalog.yaml` under `approvals:`.
   - Its runtime configuration version exactly equals the approved version.
   - Its schema passes JSON Schema draft-07 validation with `additionalProperties: false`.
2. **Catalog Immutability:** Neither the config generator nor the loader may ever mutate `catalog.yaml`. Loader runs must verify that `catalog.yaml` is treated as read-only.
3. **Zero Secret Leakage:**
   - Configuration files store secrets as `${VAR}` placeholders only.
   - The loader resolves placeholders against process environment variables, then the local `.env.mcp` file.
   - If a required variable is missing, the server is disabled (`enabled = false`) with a diagnostic log; an empty string is never substituted.
   - If an argument, environment variable, or header contains an apparent literal secret (e.g. strings starting with `sk-`, `ghp_`, `gho_`, `AKIA`, or base64 high-entropy tokens), the loader immediately halts with a fatal security violation.
   - Audit logs must sanitize all argument payloads and environment blocks, redacting potential secret keys.
4. **Workspace Confinement & Path Sanitization:**
   - Servers that manipulate files or git repositories (`filesystem`, `git`) must strictly operate inside `workspaceRoot`.
   - The `workspaceRoot` must exist, must not be equal to, located within, or contain any path listed in `forbidden_roots` (e.g. `d:/UPS_project`, `DevCrew-Vault`).
   - `workspaceRoot` must not be a filesystem root (e.g. `C:\` or `/`) or a user home directory.
   - All server command arguments referring to paths must be fully canonicalized (resolving symlinks and eliminating relative `..` segments) and verified to remain strictly within `workspaceRoot`.
5. **Untrusted Output Rule:**
   - All tool responses returned by MCP servers are untrusted text.
   - Outputs from web-browsing or fetching servers (such as Playwright or HTTP fetchers) must be treated strictly as external data, never as system instructions.
   - Any mutating or write tool invocation following the retrieval of web data must be subjected to a human confirmation gate.

---

## 3. Loader Loading & Validation Pipeline

When an orchestrator loads a crew's MCP configuration (`mcp_servers.json`):

```mermaid
flowchart TD
    A[Read mcp_servers.json] --> B[Validate against schemas/mcp_servers.schema.json]
    B -->|Schema Error| F1[Fail Closed: Abort Load]
    B -->|Pass| C[Re-verify approvals against catalog.yaml]
    C -->|Unapproved or Version Drift| F2[Refuse Server: Remove / Mark Inactive]
    C -->|Approved| D[Enforce Workspace Safety & Canonical Paths]
    D -->|Boundary Violation| F3[Fail Closed: Fatal Error]
    D -->|Pass| E[Resolve ${VAR} from Env / .env.mcp]
    E -->|Literal Secret Detected| F4[Fail Closed: Literal Secret Rejected]
    E -->|Missing Variable| W1[Disable Server: enabled = false]
    E -->|Resolved Cleanly| G[Server Ready for Gated Invocation]
```

### Step 1: Schema Validation
- The loader parses `mcp_servers.json` and evaluates it against `schemas/mcp_servers.schema.json`.
- Unknown properties at root or server level cause validation failure.

### Step 2: Runtime Approval Re-Verification
- The loader reads `catalog.yaml`.
- For each server in `mcp_servers.json`:
  - `registryName` must exist in `approvals`.
  - `version` must match the string value in `approvals[registryName]`.
- If a server has been deleted from approvals or its version was changed in `catalog.yaml`, the loader refuses to start it and logs an audit warning.

### Step 3: Workspace Boundary Verification
- The loader checks `workspaceRoot`:
  - Must exist on the filesystem.
  - Must not match or be inside any `forbidden_roots` path.
  - Any server argument representing a file path must be resolved using `os.path.realpath` / canonical path evaluation. If the resolved path does not start with `realpath(workspaceRoot)`, the loader throws a boundary violation error.

### Step 4: Secret Resolution & Literal Secret Defense
- Environment variables and header values formatted as `${VAR_NAME}` are resolved against:
  1. `os.environ`
  2. Entries in `devcrew.config.yaml` `mcp.env_file` (e.g. `.env.mcp`)
- If a required variable is missing:
  - The server's `enabled` property is switched to `false`.
  - A diagnostic message is logged: `Server '<name>' disabled: missing required environment variable '${VAR_NAME}'`.
- **Literal Secret Rejection Pattern:**
  Any string value in `env`, `headers`, or command arguments matching regex:
  `(?i)(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|gho_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|bearer\s+[a-zA-Z0-9_\-\.]{20,})`
  triggers an immediate load failure before any child process can be spawned.

---

## 4. Tool Execution Gating (`gate()`) & LangGraph Integration

Every MCP tool call triggered by an agent must pass through the gating function:

```python
gate(server_name: str, tool_name: str, arguments: dict) -> GateDecision
```
Where `GateDecision` is one of:
- `ALLOW`: Execute tool immediately without human intervention.
- `REQUIRE_APPROVAL`: Interrupt execution; pause agent state until an authorized human operator grants approval.
- `DENY`: Reject the call immediately and return an error message to the agent.

### Decision Rules:
1. If the server is not enabled or unapproved $\rightarrow$ `DENY`.
2. Check `toolPolicy` for the server:
   - If `tool_name` is in `allow`:
     - Verify server capability is not `destructive`.
     - Verify `tool_name` is NOT a write/mutation tool (e.g. `write_file`, `edit_file`, `git_push`, `git_commit`). If it is, escalate to `REQUIRE_APPROVAL`.
     - Return `ALLOW`.
   - If `tool_name` is in `requireApproval` $\rightarrow$ Return `REQUIRE_APPROVAL`.
   - Otherwise, default to `toolPolicy.default` (which defaults to `REQUIRE_APPROVAL` if unspecified).

### LangGraph Interrupt Mapping
In a LangGraph state graph:
```python
decision = loader.gate(server, tool, args)
if decision == "require_approval":
    # LangGraph interrupt pattern: pauses state machine and stores pending action
    approval = interrupt({
        "action": "mcp_tool_call",
        "server": server,
        "tool": tool,
        "arguments": sanitize_for_display(args),
        "prompt": f"Crew '{crew}' requests execution of tool '{tool}' on server '{server}'."
    })
    if not approval.get("granted"):
        audit_log.record(server, tool, decision="denied_by_user")
        return {"error": "Tool execution rejected by human operator."}
```

---

## 5. Audit Logging Specification
The loader appends structured JSON Lines (`.jsonl`) to `devcrew.config.yaml` `mcp.audit_log`:

```json
{
  "timestamp": "2026-11-09T00:15:00.000000Z",
  "crew": "devcrew",
  "server": "filesystem",
  "tool": "write_file",
  "decision": "require_approval",
  "approved_by": "user_operator",
  "execution_status": "success",
  "duration_ms": 42
}
```

**Sanitization Requirements:**
- No API tokens, keys, passwords, or bearer headers may be written to `audit_log`.
- Argument payloads containing keys matching `token`, `password`, `secret`, `key`, or `auth` must be masked with `[REDACTED]`.

---

## 6. Lifecycle & Process Management
- **Lazy Initialization:** Servers are not started at configuration load time. A server process is spawned only when its first tool is requested.
- **Process Isolation:** Stdio servers run as distinct child processes with standard input/output pipes.
- **Timeouts:** Every tool execution is bounded by `timeoutSeconds` (default: 60s). If execution exceeds this bound, the child process is terminated (SIGTERM, followed by SIGKILL after 5 seconds).
- **Restart Limits:** If a server process crashes, the loader may attempt up to 2 restarts. Subsequent crashes permanently disable the server for the duration of the crew session.
- **Crew Shutdown:** When a crew finishes, the orchestrator invokes `loader.shutdown_all()`, terminating all running child processes cleanly.

---

## 7. Skill Pairing Resolution (`servers_for_skills`)

The loader provides an API for discovering which MCP servers are relevant to a set of active skills:

```python
servers_for_skills(skill_slugs: list[str]) -> list[str]
```
- Queries `mcp_links` where `relation = 'pairs-with'`.
- Filters results to return **only** servers that are:
  1. Currently present in `DevCrew-Vault/catalog.yaml` under `approvals:`.
  2. Configured in `mcp_servers.json`.
  3. Fully resolved and `enabled = True`.
- Unapproved servers are never returned.
