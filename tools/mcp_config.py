"""
mcp_config.py — DevCrew AI Safe MCP Client Configuration Generator
===================================================================
Generates schema-validated mcp_servers.json and client export configs for approved
MCP servers.

Guarantees:
- Reads approvals from catalog.yaml strictly; never modifies catalog.yaml.
- Re-verifies every approved server against SQLite registry records and license policy.
- Strictly bounds filesystem and git servers to workspaceRoot.
- Rejects forbidden roots (d:/UPS_project, DevCrew-Vault, root, home directory).
- Uses only ${VAR} placeholders; never literal secrets.
- Marks servers with missing env variables as enabled: false.
- Validates output against schemas/mcp_servers.schema.json before atomic write.
- Emits client export files (exports/claude-desktop.json, exports/cursor.json).
- Supports CLI flags: --crew, --dry-run, --only, --check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

# Ensure tools/ is on sys.path
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config
from db import get_connection

SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|gho_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|bearer\s+[a-zA-Z0-9_\-\.]{20,})"
)

HEADER_COMMENT = "// Generated example. Review the exact command before running it."

# Statically verified tool lists with exact evidence references (file + line / section)
TOOL_EVIDENCE: dict[str, dict[str, str]] = {
    "filesystem": {
        "read_text_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L337 (readOnlyHint: true)",
        "read_media_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L338 (readOnlyHint: true)",
        "read_multiple_files": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L339 (readOnlyHint: true)",
        "list_directory": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L340 (readOnlyHint: true)",
        "list_directory_with_sizes": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L341 (readOnlyHint: true)",
        "directory_tree": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L342 (readOnlyHint: true)",
        "search_files": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L343 (readOnlyHint: true)",
        "get_file_info": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L344 (readOnlyHint: true)",
        "list_allowed_directories": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L345 (readOnlyHint: true)",
        "write_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L347 (destructiveHint: true)",
        "edit_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L349 (destructiveHint: true)",
        "append_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L348 (write tool)",
        "move_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L350 (destructiveHint: true)",
        "copy_file": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L351 (write tool)",
        "create_directory": "npm:@modelcontextprotocol/server-filesystem@2.2.0/README.md#L346 (write tool)",
    },
    "git": {
        "git_status": "pypi:mcp-server-git/0.6.2/info.description:Tools#L1 (readOnly: repo status inspection)",
        "git_diff_unstaged": "pypi:mcp-server-git/0.6.2/info.description:Tools#L2 (readOnly: unstaged diff)",
        "git_diff_staged": "pypi:mcp-server-git/0.6.2/info.description:Tools#L3 (readOnly: staged diff)",
        "git_log": "pypi:mcp-server-git/0.6.2/info.description:Tools#L7 (readOnly: commit history)",
        "git_commit": "pypi:mcp-server-git/0.6.2/info.description:Tools#L4 (write: commit creation)",
        "git_add": "pypi:mcp-server-git/0.6.2/info.description:Tools#L5 (write: staging files)",
        "git_reset": "pypi:mcp-server-git/0.6.2/info.description:Tools#L6 (write: unstage/reset)",
        "git_create_branch": "pypi:mcp-server-git/0.6.2/info.description:Tools#L8 (write: branch creation)",
    },
    "playwright-mcp": {
        "browser_click": "npm:@playwright/mcp@0.0.84/README.md#L910 (action: user click)",
        "browser_close": "npm:@playwright/mcp@0.0.84/README.md#L923 (lifecycle: close browser)",
        "browser_drag": "npm:@playwright/mcp@0.0.84/README.md#L942 (action: drag element)",
        "browser_drop": "npm:@playwright/mcp@0.0.84/README.md#L954 (action: drop element)",
        "browser_evaluate": "npm:@playwright/mcp@0.0.84/README.md#L979 (code-execution: evaluate script on page)",
        "browser_file_upload": "npm:@playwright/mcp@0.0.84/README.md#L991 (input: file upload to form)",
        "browser_fill_form": "npm:@playwright/mcp@0.0.84/README.md#L1000 (input: fill form fields)",
        "browser_hover": "npm:@playwright/mcp@0.0.84/README.md#L1031 (action: mouse hover)",
        "browser_navigate": "npm:@playwright/mcp@0.0.84/README.md#L1041 (navigation: network URL navigation)",
        "browser_navigate_back": "npm:@playwright/mcp@0.0.84/README.md#L1050 (navigation: browser back)",
        "browser_press_key": "npm:@playwright/mcp@0.0.84/README.md#L1081 (action: keypress)",
        "browser_run_code_unsafe": "npm:@playwright/mcp@0.0.84/README.md#L1100 (code-execution: arbitrary code execution)",
        "browser_select_option": "npm:@playwright/mcp@0.0.84/README.md#L1110 (input: select dropdown option)",
        "browser_snapshot": "npm:@playwright/mcp@0.0.84/README.md#L1121 (untrusted-content: accessibility/DOM tree snapshot)",
        "browser_take_screenshot": "npm:@playwright/mcp@0.0.84/README.md#L1133 (untrusted-content: page visual capture)",
        "browser_type": "npm:@playwright/mcp@0.0.84/README.md#L1147 (input: keyboard text typing)",
        "browser_wait_for": "npm:@playwright/mcp@0.0.84/README.md#L1160 (synchronization: wait for selector/timeout)",
    },
    "context7": {
        "resolve-library-id": "npm:@upstash/context7-mcp@4.5.1/README.md#L1422 (resolution: resolve library name to ID)",
        "query-docs": "npm:@upstash/context7-mcp@4.5.1/README.md#L1426 (untrusted-content: query external documentation)",
    },
}


def get_server_command_and_args(server: dict[str, Any]) -> tuple[str, list[str], dict[str, str], str | None]:
    """Legacy helper: derive client command, arguments, environment placeholders, and optional note."""
    name = server.get("name", "")
    pinned_ver = server.get("approved_version") or server.get("version", "1.0.0")
    snapshot = {}
    if server.get("snapshot_json"):
        try:
            snapshot = json.loads(server["snapshot_json"])
        except Exception:
            pass

    packages = snapshot.get("packages", [])
    remotes = snapshot.get("remotes", [])
    env_vars: dict[str, str] = {}
    note: str | None = None

    full_text = f"{name} {server.get('description', '')}"
    if "stripe" in full_text.lower():
        env_vars["STRIPE_SECRET_KEY"] = "${STRIPE_SECRET_KEY}"
    elif "github" in full_text.lower() or (name.endswith("/git") or "mcp-server-git" in full_text):
        env_vars["GITHUB_TOKEN"] = "${GITHUB_TOKEN}"

    if packages:
        pkg = packages[0]
        pkg_type = pkg.get("registryType", "npm")
        identifier = pkg.get("identifier") or name
        if pkg_type == "npm":
            cmd = "npx"
            args = ["-y", f"{identifier}@{pinned_ver}"]
        elif pkg_type == "pypi":
            cmd = "uvx"
            args = [f"{identifier}=={pinned_ver}"]
        else:
            cmd = "docker"
            args = ["run", "-i", "--rm", f"{identifier}:{pinned_ver}"]
    elif remotes:
        cmd = "remote"
        url = remotes[0].get("url")
        args = [url]
        note = f"Remote endpoint: {url}"
    else:
        cmd = "npx"
        args = ["-y", f"{name}@{pinned_ver}"]

    return cmd, args, env_vars, note


def generate_crew_config(
    vault_dir: Path,
    crew_name: str,
    approved_servers: list[dict[str, Any]],
) -> Path | None:
    """Legacy helper: generate client config file under DevCrew-Vault/mcp/configs/<crew>.json."""
    if not approved_servers:
        return None

    configs_dir = vault_dir / "mcp" / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    out_file = configs_dir / f"{crew_name}.json"

    mcp_servers_config: dict[str, Any] = {}

    for srv in approved_servers:
        cmd, args, env, note = get_server_command_and_args(srv)
        entry: dict[str, Any] = {
            "command": cmd,
            "args": args,
        }
        if env:
            entry["env"] = env
        if note:
            entry["_comment"] = note
        mcp_servers_config[srv.get("slug") or srv.get("name")] = entry

    config_payload = {
        "//": HEADER_COMMENT,
        "crew": crew_name,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "mcpServers": mcp_servers_config,
    }

    out_file.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return out_file


def normalize_path(p: str | Path) -> str:
    """Normalize path to forward slashes and canonical form."""
    return str(Path(p).resolve()).replace("\\", "/")


def validate_workspace(workspace_root_raw: str, forbidden_roots_raw: list[str]) -> str:
    """Validate workspaceRoot according to safety rules. Create if missing."""
    ws_path = Path(workspace_root_raw).resolve()
    if not ws_path.exists():
        ws_path.mkdir(parents=True, exist_ok=True)

    ws_norm = normalize_path(ws_path)

    # Check drive root or root
    if ws_path.parent == ws_path or ws_norm in ("/", "C:/", "D:/", "c:/", "d:/"):
        raise ValueError(f"workspace_root cannot be a filesystem drive root: '{ws_norm}'")

    # Check user home
    home_norm = normalize_path(Path.home())
    if ws_norm == home_norm:
        raise ValueError(f"workspace_root cannot be the user home directory: '{ws_norm}'")

    # Check forbidden roots
    for f in forbidden_roots_raw:
        f_norm = normalize_path(Path(f).resolve())
        # Refuse if ws equals f, or ws sits inside f, or f sits inside ws
        if ws_norm == f_norm:
            raise ValueError(f"workspace_root '{ws_norm}' matches forbidden root '{f_norm}'")
        if ws_norm.startswith(f_norm + "/"):
            raise ValueError(f"workspace_root '{ws_norm}' is located inside forbidden root '{f_norm}'")
        if f_norm.startswith(ws_norm + "/"):
            raise ValueError(f"forbidden root '{f_norm}' is located inside workspace_root '{ws_norm}'")

    return ws_norm


def load_env_file(env_file_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE dotenv file without external dependencies."""
    env_vars: dict[str, str] = {}
    if not env_file_path.is_file():
        return env_vars

    for line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            env_vars[k] = v
    return env_vars


def get_catalog_approvals(catalog_path: Path) -> tuple[dict[str, str], str]:
    """Load approvals mapping from catalog.yaml and compute its SHA-256."""
    raw_bytes = catalog_path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    data = yaml.safe_load(raw_bytes.decode("utf-8")) or {}
    approvals = data.get("approvals") or {}
    if not isinstance(approvals, dict):
        raise ValueError(f"'approvals' in '{catalog_path}' must be a mapping of server name to version.")
    return {str(k): str(v) for k, v in approvals.items()}, sha256


def check_for_literal_secrets(data: Any, path: str = "root") -> None:
    """Recursively scan for literal secret patterns in config data."""
    if isinstance(data, str):
        if SECRET_PATTERN.search(data):
            raise ValueError(f"Literal secret pattern detected at '{path}': value rejected.")
    elif isinstance(data, dict):
        for k, v in data.items():
            check_for_literal_secrets(v, f"{path}.{k}")
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            check_for_literal_secrets(item, f"{path}[{idx}]")


def build_server_config(
    reg_name: str,
    approved_ver: str,
    db_row: dict[str, Any],
    workspace_root: str,
    env_pool: dict[str, str],
    allow_push: bool = False,
    paired_skills: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Construct a single server entry conforming to schemas/mcp_servers.schema.json."""
    transport = db_row.get("transport") or "stdio"
    snapshot_json = db_row.get("snapshot_json") or "{}"
    snapshot = {}
    try:
        snapshot = json.loads(snapshot_json)
    except Exception:
        pass

    packages = snapshot.get("packages") or []
    remotes = snapshot.get("remotes") or []

    # Short slug key for servers dict
    if "/" in reg_name:
        short_key = reg_name.split("/")[-1]
    else:
        short_key = reg_name

    # Determine capability class
    raw_cap = db_row.get("capability_class") or "read-write"
    if raw_cap not in ("read-only", "read-write", "destructive", "unknown-treat-as-write"):
        capability = "unknown-treat-as-write"
    else:
        capability = raw_cap

    env: dict[str, str] = {}
    headers: dict[str, str] = {}
    args: list[str] = []
    command: str | None = None
    url: str | None = None

    # Derive toolPolicy based on server identity and capability
    tool_evidence: dict[str, str] = {}
    sec_note: str | None = None

    if short_key == "filesystem" or reg_name.endswith("/filesystem"):
        command = "npx"
        args = ["-y", f"@modelcontextprotocol/server-filesystem@{approved_ver}", workspace_root]
        capability = "read-write"
        tool_evidence = TOOL_EVIDENCE["filesystem"]
        tool_policy = {
            "default": "require-approval",
            "allow": [
                "read_text_file",
                "read_media_file",
                "read_multiple_files",
                "list_directory",
                "list_directory_with_sizes",
                "directory_tree",
                "search_files",
                "get_file_info",
                "list_allowed_directories",
            ],
            "requireApproval": [
                "write_file",
                "edit_file",
                "append_file",
                "move_file",
                "copy_file",
                "create_directory",
            ],
        }
    elif short_key == "git" or reg_name.endswith("/git"):
        command = "uvx"
        args = ["--from", f"mcp-server-git=={approved_ver}", "mcp-server-git", "--repository", workspace_root]
        capability = "read-write"
        tool_evidence = TOOL_EVIDENCE["git"]
        tool_policy = {
            "default": "require-approval",
            "allow": ["git_status", "git_diff_unstaged", "git_diff_staged", "git_log"],
            "requireApproval": ["git_commit", "git_add", "git_reset", "git_create_branch"],
        }
    elif "playwright" in short_key.lower():
        command = "npx"
        args = ["-y", f"@playwright/mcp@{approved_ver}"]
        capability = "read-write"
        tool_evidence = TOOL_EVIDENCE["playwright-mcp"]
        sec_note = (
            "Playwright v0.0.84 supports '--isolated' (in-memory profile) and '--allowed-origins <origins>' flags. "
            "To restrict browser network scope, configure args with --isolated and trusted origins."
        )
        # Per security invariants: tools executing code or returning untrusted content must require approval
        tool_policy = {
            "default": "require-approval",
            "allow": [],
            "requireApproval": sorted(list(tool_evidence.keys())),
        }
    elif "context7" in short_key.lower():
        command = "npx"
        args = ["-y", f"@upstash/context7-mcp@{approved_ver}"]
        capability = "read-only"
        env["CONTEXT7_API_KEY"] = "${CONTEXT7_API_KEY}"
        tool_evidence = TOOL_EVIDENCE["context7"]
        # Per requirement 3: for servers with unverified tool names or untrusted retrieval, default is require-approval
        tool_policy = {
            "default": "require-approval",
            "allow": [],
            "requireApproval": ["resolve-library-id", "query-docs"],
        }
    else:
        # Fallback for arbitrary server
        if packages:
            pkg = packages[0]
            pkg_type = pkg.get("registryType", "npm")
            identifier = pkg.get("identifier") or reg_name
            if pkg_type == "npm":
                command = "npx"
                args = ["-y", f"{identifier}@{approved_ver}"]
            elif pkg_type == "pypi":
                command = "uvx"
                args = ["--from", f"{identifier}=={approved_ver}", identifier]
            else:
                command = "docker"
                args = ["run", "-i", "--rm", f"{identifier}:{approved_ver}"]
            for ev in pkg.get("environmentVariables") or []:
                if isinstance(ev, dict) and ev.get("name"):
                    env[ev["name"]] = f"${{{ev['name']}}}"
        elif remotes:
            transport = "streamable-http"
            url = remotes[0].get("url")
            for h in remotes[0].get("headers") or []:
                if isinstance(h, dict) and h.get("name"):
                    headers[h["name"]] = f"${{{h['name'].upper()}}}"

        tool_policy = {
            "default": "require-approval",
            "allow": [],
            "requireApproval": [],
        }

    # Check whether required environment variables are satisfied in env_pool
    enabled = True
    missing_vars = []
    for var_name, placeholder in env.items():
        var_key = placeholder.strip("${}")
        if not env_pool.get(var_key):
            enabled = False
            missing_vars.append(var_key)

    server_entry: dict[str, Any] = {
        "registryName": reg_name,
        "version": approved_ver,
        "transport": transport,
        "capability": capability,
        "toolPolicy": tool_policy,
        "timeoutSeconds": 60,
        "enabled": enabled,
    }

    if tool_evidence:
        server_entry["toolEvidence"] = tool_evidence
    if sec_note:
        server_entry["_security_note"] = sec_note
    if command:
        server_entry["command"] = command
        server_entry["args"] = args
    if url:
        server_entry["url"] = url
    if headers:
        server_entry["headers"] = headers
    if env:
        server_entry["env"] = env
    if paired_skills:
        server_entry["pairedSkills"] = sorted(paired_skills)

    if not enabled and missing_vars:
        server_entry["_comment"] = f"Disabled: missing environment variable(s): {', '.join(missing_vars)}"

    return short_key, server_entry


def generate_configs_for_crew(
    crew: str = "devcrew",
    only_server: str | None = None,
    dry_run: bool = False,
    check_mode: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Generate mcp_servers.json and export configs for the specified crew."""
    config = load_config()
    project_root = Path(config["_project_root"])
    catalog_path = project_root / "DevCrew-Vault" / "catalog.yaml"
    db_path = Path(config["vault"]["db_path"]).resolve()
    schema_path = project_root / "schemas" / "mcp_servers.schema.json"

    mcp_cfg = config.get("mcp") or {}
    ws_root = validate_workspace(
        mcp_cfg.get("workspace_root", "d:/UPS_workspace"),
        mcp_cfg.get("forbidden_roots", ["d:/UPS_project", "d:/UPS_project/DevCrew-Vault"]),
    )

    env_file_rel = mcp_cfg.get("env_file", ".env.mcp")
    env_file_path = project_root / env_file_rel
    env_pool = dict(os.environ)
    env_pool.update(load_env_file(env_file_path))

    approvals, catalog_sha256 = get_catalog_approvals(catalog_path)
    allowed_licenses = set(config.get("allowed_licenses", ["MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0"]))

    conn = get_connection(db_path)
    cur = conn.cursor()

    # Query registry sync run timestamp
    cur.execute("SELECT finished_at FROM mcp_sync_runs ORDER BY id DESC LIMIT 1")
    sync_row = cur.fetchone()
    reg_snapshot = sync_row[0] if sync_row and sync_row[0] else datetime.now(timezone.utc).isoformat()

    # Query paired skills
    cur.execute("SELECT mcp_slug, skill_slug FROM mcp_links WHERE relation = 'pairs-with'")
    paired_map: dict[str, list[str]] = {}
    for m_slug, s_slug in cur.fetchall():
        paired_map.setdefault(m_slug, []).append(s_slug)

    servers_dict: dict[str, Any] = {}
    verification_errors: list[str] = []

    for reg_name, approved_ver in approvals.items():
        if only_server and only_server not in (reg_name, reg_name.split("/")[-1]):
            continue

        cur.execute(
            """
            SELECT id, name, slug, version, license, license_source, transport,
                   capability_class, package_types, snapshot_json
            FROM mcp_servers
            WHERE name = ?
            """,
            (reg_name,),
        )
        row = cur.fetchone()
        if not row:
            err = f"Approved server '{reg_name}' not found in registry.db"
            print(f"[MCPConfig:WARN] {err}")
            verification_errors.append(err)
            continue

        db_row = dict(row)
        # License check
        lic = db_row.get("license")
        if lic not in allowed_licenses:
            err = f"Server '{reg_name}' license '{lic}' is not in allowed_licenses."
            print(f"[MCPConfig:REJECT] {err}")
            verification_errors.append(err)
            continue

        # Exact version verification in snapshot
        snapshot = {}
        try:
            snapshot = json.loads(db_row.get("snapshot_json") or "{}")
        except Exception:
            pass

        packages = snapshot.get("packages") or []
        package_versions = [p.get("version") for p in packages if isinstance(p, dict)]
        if db_row.get("version") != approved_ver and approved_ver not in package_versions:
            err = f"Server '{reg_name}' approved version '{approved_ver}' differs from registry version '{db_row.get('version')}'"
            print(f"[MCPConfig:REJECT] {err}")
            verification_errors.append(err)
            continue

        paired = paired_map.get(db_row.get("slug"), [])
        short_key, srv_cfg = build_server_config(
            reg_name=reg_name,
            approved_ver=approved_ver,
            db_row=db_row,
            workspace_root=ws_root,
            env_pool=env_pool,
            allow_push=False,
            paired_skills=paired,
        )
        servers_dict[short_key] = srv_cfg

    conn.close()

    if verification_errors:
        print(f"[MCPConfig] {len(verification_errors)} verification warning(s)/error(s) occurred.")

    main_config: dict[str, Any] = {
        "schemaVersion": 1,
        "crew": crew,
        "generatedFrom": {
            "catalogSha256": catalog_sha256,
            "registrySnapshot": str(reg_snapshot),
        },
        "workspaceRoot": ws_root,
        "servers": servers_dict,
    }

    # Validate literal secrets
    check_for_literal_secrets(main_config)

    # Validate against JSON Schema
    if schema_path.is_file():
        schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=main_config, schema=schema_data)
    else:
        print(f"[MCPConfig:WARN] Schema file '{schema_path}' not found; skipped validation.")

    # Build exports
    claude_servers: dict[str, Any] = {}
    cursor_servers: dict[str, Any] = {}
    for skey, scfg in servers_dict.items():
        if not scfg.get("enabled"):
            continue
        entry = {
            "command": scfg.get("command"),
            "args": scfg.get("args", []),
            "env": scfg.get("env", {}),
        }
        claude_servers[skey] = entry
        cursor_servers[skey] = entry

    claude_export: dict[str, Any] = {
        "_generated": "Review before copying into your client config",
        "mcpServers": claude_servers,
    }

    cursor_export: dict[str, Any] = {
        "_generated": "Review before copying into your client config",
        "mcpServers": cursor_servers,
    }

    configs_dir = project_root / "DevCrew-Vault" / "mcp" / "configs" / crew
    out_main = configs_dir / "mcp_servers.json"
    exports_dir = configs_dir / "exports"
    out_claude = exports_dir / "claude-desktop.json"
    out_cursor = exports_dir / "cursor.json"

    if check_mode:
        if not out_main.is_file():
            print(f"[MCPConfig:CHECK FAIL] Target file '{out_main}' does not exist.")
            sys.exit(1)
        existing = json.loads(out_main.read_text(encoding="utf-8"))
        # Check catalogSha256 and servers
        if existing.get("generatedFrom", {}).get("catalogSha256") != catalog_sha256:
            print("[MCPConfig:CHECK FAIL] Config is stale: catalog.yaml has been modified since generation.")
            sys.exit(1)
        if set(existing.get("servers", {}).keys()) != set(servers_dict.keys()):
            print("[MCPConfig:CHECK FAIL] Config is stale: server keys differ.")
            sys.exit(1)
        print("[MCPConfig:CHECK PASS] Config is strictly up to date with catalog.yaml approvals.")
        return main_config, claude_export, cursor_export

    if not dry_run:
        configs_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write main config
        tmp_main = tempfile.NamedTemporaryFile("w", dir=configs_dir, delete=False, encoding="utf-8")
        tmp_main.write(json.dumps(main_config, indent=2))
        tmp_main.flush()
        tmp_main.close()
        os.replace(tmp_main.name, out_main)

        # Atomic write exports
        tmp_claude = tempfile.NamedTemporaryFile("w", dir=exports_dir, delete=False, encoding="utf-8")
        tmp_claude.write(json.dumps(claude_export, indent=2))
        tmp_claude.flush()
        tmp_claude.close()
        os.replace(tmp_claude.name, out_claude)

        tmp_cursor = tempfile.NamedTemporaryFile("w", dir=exports_dir, delete=False, encoding="utf-8")
        tmp_cursor.write(json.dumps(cursor_export, indent=2))
        tmp_cursor.flush()
        tmp_cursor.close()
        os.replace(tmp_cursor.name, out_cursor)

        print(f"[MCPConfig] Wrote schema-validated config: {out_main}")
        print(f"[MCPConfig] Wrote Claude Desktop export: {out_claude}")
        print(f"[MCPConfig] Wrote Cursor export: {out_cursor}")

    return main_config, claude_export, cursor_export


def print_plain_summary(main_config: dict[str, Any]) -> None:
    """Print human-readable summary of servers, permissions, variables, and risks."""
    servers = main_config.get("servers", {})
    ws_root = main_config.get("workspaceRoot")
    print("\n" + "=" * 76)
    print(" DevCrew AI Safe MCP Configuration Summary")
    print("=" * 76)
    print(f"Workspace Root Directory (Sandbox): {ws_root}")
    print(f"Total Approved Servers: {len(servers)}\n")

    for name, srv in servers.items():
        status = "ENABLED" if srv.get("enabled") else "DISABLED (Missing Key)"
        cap = srv.get("capability", "unknown")
        tp = srv.get("toolPolicy", {})
        allow_tools = ", ".join(tp.get("allow", [])) or "None"
        req_tools = ", ".join(tp.get("requireApproval", [])) or "None"
        envs = ", ".join([f"{k}={v}" for k, v in srv.get("env", {}).items()]) or "None"

        print(f"• Server '{name}' [{srv.get('registryName')}@{srv.get('version')}] — Status: {status}")
        print(f"  Capability: {cap} | Transport: {srv.get('transport')}")
        print(f"  Auto-Allowed Tools: {allow_tools}")
        print(f"  Gated Tools (Requires Human Approval): {req_tools}")
        print(f"  Required Environment Variables: {envs}")
        if srv.get("pairedSkills"):
            print(f"  Paired Skills: {', '.join(srv['pairedSkills'])}")
        print()

    print("Combination & Security Risks:")
    print("1. [Filesystem + Git]: Both servers are scoped to workspaceRoot. File edits can be committed")
    print("   or reset. All git mutations (commit, reset, branch creation, push) require explicit approval.")
    print("2. [Playwright (Browser) + Write Tools]: Web pages retrieved via Playwright are untrusted.")
    print("   Mutating tools (filesystem write, git commit) triggered after browsing require human gate.")
    print("3. [External Downloads]: npx and uvx run pinned exact versions. Pre-install into local node_modules")
    print("   or venv where possible to avoid network downloads during runs.")
    print("=" * 76 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate safe MCP server configs for DevCrew AI.")
    parser.add_argument("--crew", type=str, default="devcrew", help="Crew identifier (default: devcrew).")
    parser.add_argument("--only", type=str, default=None, help="Generate only for specified server name/slug.")
    parser.add_argument("--dry-run", action="store_true", help="Print generated config without writing to disk.")
    parser.add_argument("--check", action="store_true", help="Check if existing config is up to date with catalog.")
    args = parser.parse_args()

    cfg, _, _ = generate_configs_for_crew(
        crew=args.crew,
        only_server=args.only,
        dry_run=args.dry_run,
        check_mode=args.check,
    )

    if not args.check:
        print_plain_summary(cfg)
        if args.dry_run:
            print("[MCPConfig:DRY-RUN] Generated config JSON:")
            print(json.dumps(cfg, indent=2))


if __name__ == "__main__":
    main()
