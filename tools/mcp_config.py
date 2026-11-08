"""
mcp_config.py — DevCrew MCP Client Configuration Generator
==========================================================
Generates example client configuration JSON for human-approved MCP servers.
Enforces safety rules:
- Writes ONLY into DevCrew-Vault/mcp/configs/
- Strictly requires status = 'approved' (refuses to write if no servers approved)
- Uses exact pinned version
- Uses environment variable placeholders (${VAR}), NEVER real secrets
- Where read-only mode exists, defaults to it with a comment

CLI:
    python tools/mcp_config.py --crew <name>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure tools/ is on sys.path
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config
from db import get_connection, list_mcp_servers


HEADER_COMMENT = "// Generated example. Review the exact command before running it."


def get_server_command_and_args(server: dict[str, Any]) -> tuple[str, list[str], dict[str, str], str | None]:
    """Derive client command, arguments, environment placeholders, and optional note."""
    name = server.get("name", "")
    slug = server.get("slug", "")
    pinned_ver = server.get("approved_version") or server.get("version", "1.0.0")
    pkg_types = server.get("package_types", "")
    transport = server.get("transport", "stdio")

    snapshot = {}
    if server.get("snapshot_json"):
        try:
            snapshot = json.loads(server["snapshot_json"])
        except Exception:
            snapshot = {}

    packages = snapshot.get("packages", [])
    remotes = snapshot.get("remotes", [])

    env_vars: dict[str, str] = {}
    note: str | None = None

    # Derive env vars placeholders
    full_text = f"{name} {server.get('description', '')}"
    if "stripe" in full_text.lower():
        env_vars["STRIPE_SECRET_KEY"] = "${STRIPE_SECRET_KEY}"
    elif "github" in full_text.lower() or "git" in full_text.lower():
        env_vars["GITHUB_TOKEN"] = "${GITHUB_TOKEN}"
    elif "cloudflare" in full_text.lower():
        env_vars["CLOUDFLARE_API_TOKEN"] = "${CLOUDFLARE_API_TOKEN}"
    elif "sentry" in full_text.lower():
        env_vars["SENTRY_AUTH_TOKEN"] = "${SENTRY_AUTH_TOKEN}"
    elif "neon" in full_text.lower():
        env_vars["NEON_API_KEY"] = "${NEON_API_KEY}"
    elif "clickhouse" in full_text.lower():
        env_vars["CLICKHOUSE_HOST"] = "${CLICKHOUSE_HOST}"
        env_vars["CLICKHOUSE_USER"] = "${CLICKHOUSE_USER}"
        env_vars["CLICKHOUSE_PASSWORD"] = "${CLICKHOUSE_PASSWORD}"
    elif "figma" in full_text.lower():
        env_vars["FIGMA_ACCESS_TOKEN"] = "${FIGMA_ACCESS_TOKEN}"
    elif "exa" in full_text.lower():
        env_vars["EXA_API_KEY"] = "${EXA_API_KEY}"
    elif "firecrawl" in full_text.lower():
        env_vars["FIRECRAWL_API_KEY"] = "${FIRECRAWL_API_KEY}"

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
        note = f"Remote endpoint ({transport}): {url}"
    else:
        cmd = "npx"
        args = ["-y", f"{name}@{pinned_ver}"]

    if server.get("capability_class") in ("read-only", "read-write") and "read-only" in full_text.lower():
        if "--read-only" not in args:
            args.append("--read-only")
            note = (note + "; " if note else "") + "Defaulted to read-only mode for safety."

    return cmd, args, env_vars, note


def generate_crew_config(
    vault_dir: Path,
    crew_name: str,
    approved_servers: list[dict[str, Any]],
) -> Path | None:
    """Generate client config file under DevCrew-Vault/mcp/configs/<crew>.json."""
    if not approved_servers:
        print("[MCPConfig] No approved MCP servers found in catalog.yaml. Review MCP-APPROVALS-NEEDED.md to approve servers.")
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
        mcp_servers_config[srv["slug"]] = entry

    config_payload = {
        "//": HEADER_COMMENT,
        "crew": crew_name,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "mcpServers": mcp_servers_config,
    }

    out_file.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    print(f"[MCPConfig] Generated example client config for crew '{crew_name}' at {out_file}")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate example MCP client configuration for approved servers.")
    parser.add_argument("--crew", type=str, required=True, help="Crew or team name for config grouping.")
    args = parser.parse_args()

    config = load_config()
    vault_dir = Path(config["vault"]["db_path"]).resolve().parent
    db_path = Path(config["vault"]["db_path"]).resolve()

    conn = get_connection(db_path)
    approved_servers = list_mcp_servers(conn, status="approved")
    conn.close()

    generate_crew_config(vault_dir, args.crew, approved_servers)


if __name__ == "__main__":
    main()

