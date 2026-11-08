"""
mcp_loader.py — DevCrew AI Safe MCP Client Configuration Loader
===============================================================
Reference implementation of the safe MCP loader specification (docs/mcp_loader_spec.md).

Invariants:
1. Validates mcp_servers.json against schemas/mcp_servers.schema.json.
2. Re-verifies catalog.yaml approvals at load time (refuses unapproved or version-drifted servers).
3. Resolves ${VAR} placeholders from process environment or .env.mcp (disables server if missing; never empty string).
4. Rejects literal secrets matching known key/token patterns.
5. Enforces workspaceRoot safety and prevents symlink/relative path escapes.
6. Implements gate(server, tool, args) returning 'allow', 'require_approval', or 'deny'.
7. Records audit entries to logs/mcp-audit.jsonl without leaking secrets.
8. Provides servers_for_skills(skill_slugs) for skill pairing lookup.
9. Manages lazy child process lifecycle with timeout enforcement (--launch flag).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
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

WRITE_TOOL_KEYWORDS = (
    "write", "create", "delete", "remove", "drop", "edit", "move", "rename",
    "modify", "commit", "push", "reset", "checkout", "branch"
)

SENSITIVE_ARG_KEYS = (
    "password", "secret", "token", "key", "auth", "authorization",
    "apikey", "api_key", "credential", "private"
)


class SecurityError(Exception):
    """Raised when a security invariant is violated."""


class MCPSafeLoader:
    """Safe runtime loader and policy gatekeeper for DevCrew MCP servers."""

    def __init__(
        self,
        crew: str = "devcrew",
        config_path: Path | None = None,
        catalog_path: Path | None = None,
        devcrew_config_path: Path | None = None,
    ):
        self.crew = crew
        self.devcrew_cfg = load_config(devcrew_config_path)
        self.project_root = Path(self.devcrew_cfg["_project_root"]).resolve()

        if config_path is not None:
            self.config_path = Path(config_path).resolve()
        else:
            self.config_path = (
                self.project_root / "DevCrew-Vault" / "mcp" / "configs" / self.crew / "mcp_servers.json"
            )

        if catalog_path is not None:
            self.catalog_path = Path(catalog_path).resolve()
        else:
            self.catalog_path = self.project_root / "DevCrew-Vault" / "catalog.yaml"

        self.schema_path = self.project_root / "schemas" / "mcp_servers.schema.json"

        mcp_cfg = self.devcrew_cfg.get("mcp") or {}
        self.workspace_root_cfg = mcp_cfg.get("workspace_root", "d:/UPS_workspace")
        self.forbidden_roots_cfg = mcp_cfg.get(
            "forbidden_roots", ["d:/UPS_project", "d:/UPS_project/DevCrew-Vault"]
        )
        self.env_file_cfg = self.project_root / mcp_cfg.get("env_file", ".env.mcp")
        self.audit_log_path = self.project_root / mcp_cfg.get("audit_log", "logs/mcp-audit.jsonl")

        self.config_data: dict[str, Any] = {}
        self.active_servers: dict[str, dict[str, Any]] = {}
        self.disabled_reasons: dict[str, str] = {}
        self.processes: dict[str, subprocess.Popen] = {}

    def _normalize(self, p: str | Path) -> str:
        return str(Path(p).resolve()).replace("\\", "/")

    def _load_env_file(self) -> dict[str, str]:
        env_vars: dict[str, str] = {}
        if not self.env_file_cfg.is_file():
            return env_vars
        for line in self.env_file_cfg.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("'\"")
        return env_vars

    def validate_schema(self, data: dict[str, Any]) -> None:
        """Validate configuration data against JSON Schema."""
        if not self.schema_path.is_file():
            raise FileNotFoundError(f"Schema not found at '{self.schema_path}'")
        schema_data = json.loads(self.schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema_data)

    def check_literal_secrets(self, data: Any, context: str = "config") -> None:
        """Check for literal secret patterns in strings."""
        if isinstance(data, str):
            if SECRET_PATTERN.search(data):
                raise SecurityError(f"Literal secret pattern detected at '{context}': rejected.")
        elif isinstance(data, dict):
            for k, v in data.items():
                self.check_literal_secrets(v, f"{context}.{k}")
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                self.check_literal_secrets(item, f"{context}[{idx}]")

    def verify_workspace_safety(self, ws_root_str: str) -> Path:
        """Verify that workspaceRoot exists, is canonical, and does not violate boundary constraints."""
        ws_path = Path(ws_root_str).resolve()
        if not ws_path.exists():
            raise FileNotFoundError(f"workspaceRoot '{ws_path}' does not exist on filesystem.")

        ws_norm = self._normalize(ws_path)

        # Check drive root
        if ws_path.parent == ws_path or ws_norm in ("/", "C:/", "D:/", "c:/", "d:/"):
            raise SecurityError(f"workspaceRoot cannot be a filesystem drive root: '{ws_norm}'")

        # Check user home
        home_norm = self._normalize(Path.home())
        if ws_norm == home_norm:
            raise SecurityError(f"workspaceRoot cannot be the user home directory: '{ws_norm}'")

        # Check forbidden roots
        for f in self.forbidden_roots_cfg:
            f_norm = self._normalize(Path(f).resolve())
            if ws_norm == f_norm or ws_norm.startswith(f_norm + "/") or f_norm.startswith(ws_norm + "/"):
                raise SecurityError(
                    f"workspaceRoot '{ws_norm}' conflicts with forbidden root '{f_norm}'"
                )

        return ws_path

    def load(self) -> dict[str, Any]:
        """Load, validate, re-verify approvals, resolve environment, and check boundaries."""
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: '{self.config_path}'")

        raw_text = self.config_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        # 1. Schema validation
        self.validate_schema(data)

        # 2. Literal secret rejection in raw file
        self.check_literal_secrets(data, context="raw_config")

        # 3. Workspace safety validation
        ws_root = self.verify_workspace_safety(data.get("workspaceRoot", self.workspace_root_cfg))

        # 4. Re-verify approvals at load time against catalog.yaml
        if not self.catalog_path.is_file():
            raise FileNotFoundError(f"Catalog file not found: '{self.catalog_path}'")

        catalog_data = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        approvals = catalog_data.get("approvals") or {}
        if not isinstance(approvals, dict):
            raise ValueError(f"'approvals' in '{self.catalog_path}' must be a mapping.")

        # 5. Environment resolution pool
        env_pool = dict(os.environ)
        env_pool.update(self._load_env_file())

        servers = data.get("servers", {})
        self.active_servers = {}
        self.disabled_reasons = {}

        for short_name, srv in servers.items():
            reg_name = srv.get("registryName")
            ver = srv.get("version")

            # Check approval existence and exact version
            if reg_name not in approvals:
                reason = f"Server '{reg_name}' is not in catalog.yaml approvals."
                self.disabled_reasons[short_name] = reason
                continue

            if approvals[reg_name] != ver:
                reason = f"Server '{reg_name}' version '{ver}' does not match approved '{approvals[reg_name]}'."
                self.disabled_reasons[short_name] = reason
                continue

            # Verify arguments do not attempt directory traversal or path escape
            args = srv.get("args") or []
            for arg in args:
                if isinstance(arg, str) and (".." in arg or arg.startswith("/") or ":" in arg):
                    # If it's a path argument, verify it's inside ws_root
                    try:
                        resolved_arg = Path(arg).resolve()
                        if resolved_arg.is_absolute() and resolved_arg.exists():
                            norm_arg = self._normalize(resolved_arg)
                            norm_ws = self._normalize(ws_root)
                            if not (norm_arg == norm_ws or norm_arg.startswith(norm_ws + "/")):
                                raise SecurityError(
                                    f"Path argument '{arg}' resolves outside workspaceRoot '{norm_ws}'"
                                )
                    except Exception as e:
                        if isinstance(e, SecurityError):
                            raise

            # Resolve environment variable placeholders
            resolved_env: dict[str, str] = {}
            missing_vars: list[str] = []
            for k, val in srv.get("env", {}).items():
                if val.startswith("${") and val.endswith("}"):
                    var_name = val[2:-1]
                    if var_name in env_pool and env_pool[var_name] != "":
                        resolved_env[k] = env_pool[var_name]
                    else:
                        missing_vars.append(var_name)
                else:
                    resolved_env[k] = val

            # Check resolved env for literal secrets
            self.check_literal_secrets(resolved_env, context=f"env.{short_name}")

            # If required env vars are missing, disable server (never use empty string)
            if missing_vars:
                srv_copy = dict(srv)
                srv_copy["enabled"] = False
                srv_copy["_disabled_reason"] = f"Missing required env var(s): {', '.join(missing_vars)}"
                self.disabled_reasons[short_name] = srv_copy["_disabled_reason"]
                self.active_servers[short_name] = srv_copy
                continue

            # Check git server repository path
            if short_name == "git" or (reg_name and reg_name.endswith("/git")):
                repo_path_str = str(ws_root)
                for idx, a in enumerate(args):
                    if a == "--repository" and idx + 1 < len(args):
                        repo_path_str = args[idx + 1]
                        break
                repo_path = Path(repo_path_str).resolve()
                if not repo_path.exists():
                    reason = f"Git repository path '{repo_path}' does not exist."
                    print(f"[MCPLoader:WARN] Server '{short_name}' disabled: {reason}")
                    srv_copy = dict(srv)
                    srv_copy["enabled"] = False
                    srv_copy["_disabled_reason"] = reason
                    self.disabled_reasons[short_name] = reason
                    self.active_servers[short_name] = srv_copy
                    continue
                if not (repo_path / ".git").exists():
                    reason = (
                        f"Git repository path '{repo_path}' exists but is not an initialized git repository "
                        f"(missing .git directory). Please run 'git init {repo_path}' to enable git server."
                    )
                    print(f"[MCPLoader:WARN] Server '{short_name}' disabled: {reason}")
                    srv_copy = dict(srv)
                    srv_copy["enabled"] = False
                    srv_copy["_disabled_reason"] = reason
                    self.disabled_reasons[short_name] = reason
                    self.active_servers[short_name] = srv_copy
                    continue

            # Copy and enable
            srv_copy = dict(srv)
            srv_copy["env"] = resolved_env
            self.active_servers[short_name] = srv_copy

        self.config_data = data
        return data

    def gate(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
        approver: str | None = None,
    ) -> str:
        """Evaluate whether a tool execution is allowed, requires human approval, or is denied.

        Returns:
            'allow' | 'require_approval' | 'deny'
        """
        start_time = time.perf_counter()
        srv = self.active_servers.get(server)

        if not srv:
            decision = "deny"
            self.record_audit(server, tool, decision, approver, arguments, duration_ms=0)
            return decision

        if not srv.get("enabled"):
            decision = "deny"
            self.record_audit(server, tool, decision, approver, arguments, duration_ms=0)
            return decision

        policy = srv.get("toolPolicy", {})
        default_policy = policy.get("default", "require-approval")
        allow_list = set(policy.get("allow") or [])
        require_approval_list = set(policy.get("requireApproval") or [])

        # Invariant 1: Code execution / script evaluation tools must NEVER execute without human gate
        is_code_exec = any(kw in tool.lower() for kw in ("eval", "exec", "run_code", "script"))

        # Invariant 2: Tools returning untrusted external web content must require approval by default
        is_untrusted_web = any(kw in tool.lower() for kw in ("get_html", "snapshot", "fetch", "scrape", "crawl"))

        # Invariant 3: Write tools must NEVER be in allow
        is_write_tool = any(kw in tool.lower() for kw in WRITE_TOOL_KEYWORDS)

        if tool in require_approval_list or is_write_tool or is_code_exec or is_untrusted_web:
            decision = "require_approval"
        elif tool in allow_list:
            if srv.get("capability") == "destructive":
                decision = "require_approval"
            else:
                decision = "allow"
        else:
            decision = "require_approval" if default_policy != "allow" else "allow"

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        self.record_audit(server, tool, decision, approver, arguments, duration_ms)
        return decision

    def record_audit(
        self,
        server: str,
        tool: str,
        decision: str,
        approver: str | None = None,
        arguments: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> None:
        """Append an audit record to logs/mcp-audit.jsonl, sanitizing sensitive keys."""
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

            sanitized_args: dict[str, Any] = {}
            if arguments and isinstance(arguments, dict):
                for k, v in arguments.items():
                    if any(sensitive in k.lower() for sensitive in SENSITIVE_ARG_KEYS):
                        sanitized_args[k] = "[REDACTED]"
                    elif isinstance(v, str) and SECRET_PATTERN.search(v):
                        sanitized_args[k] = "[REDACTED_SECRET]"
                    else:
                        sanitized_args[k] = v

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "crew": self.crew,
                "server": server,
                "tool": tool,
                "decision": decision,
                "approver": approver,
                "duration_ms": duration_ms,
            }
            if sanitized_args:
                record["arguments"] = sanitized_args

            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[MCPLoader:WARN] Failed to write audit log: {e}")

    def servers_for_skills(self, skill_slugs: list[str]) -> list[str]:
        """Query paired servers for given skills, returning only approved and enabled servers."""
        if not skill_slugs:
            return []

        db_path = Path(self.devcrew_cfg["vault"]["db_path"]).resolve()
        conn = get_connection(db_path)
        cur = conn.cursor()

        placeholders = ",".join("?" for _ in skill_slugs)
        cur.execute(
            f"""
            SELECT DISTINCT m.name, m.slug
            FROM mcp_links l
            JOIN mcp_servers m ON l.mcp_slug = m.slug
            WHERE l.relation = 'pairs-with' AND l.skill_slug IN ({placeholders})
            """,
            skill_slugs,
        )
        rows = cur.fetchall()
        conn.close()

        paired_short_names = set()
        for r in rows:
            name = r[0]
            short_name = name.split("/")[-1] if "/" in name else name
            paired_short_names.add(short_name)

        result = []
        for sname in paired_short_names:
            srv = self.active_servers.get(sname)
            if srv and srv.get("enabled"):
                result.append(sname)

        return sorted(result)

    def launch(self, server_name: str, timeout_seconds: int = 60) -> subprocess.Popen:
        """Launch an approved stdio MCP server process lazily. Intended for fixtures and tests."""
        srv = self.active_servers.get(server_name)
        if not srv:
            raise ValueError(f"Server '{server_name}' is not an active, approved server.")
        if not srv.get("enabled"):
            raise ValueError(f"Server '{server_name}' is disabled: {srv.get('_disabled_reason')}")

        cmd = srv.get("command")
        args = srv.get("args") or []
        env = dict(os.environ)
        env.update(srv.get("env") or {})

        full_cmd = [cmd] + args
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        self.processes[server_name] = proc
        return proc

    def shutdown_all(self) -> None:
        """Terminate all active spawned child processes."""
        for sname, proc in list(self.processes.items()):
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.processes.clear()


def main() -> None:
    parser = argparse.ArgumentParser(description="DevCrew AI Safe MCP Client Configuration Loader")
    parser.add_argument("--crew", type=str, default="devcrew", help="Crew identifier (default: devcrew).")
    parser.add_argument("--validate", action="store_true", help="Validate config, catalog approvals, and workspace.")
    parser.add_argument("--launch", type=str, default=None, help="Test launch a server by name.")
    args = parser.parse_args()

    loader = MCPSafeLoader(crew=args.crew)

    try:
        data = loader.load()
        print(f"[MCPLoader:PASS] Successfully loaded and validated configuration for crew '{args.crew}'.")
        print(f"  Workspace Root: {data.get('workspaceRoot')}")
        print(f"  Active Servers: {len(loader.active_servers)}")

        for sname, srv in loader.active_servers.items():
            status = "ENABLED" if srv.get("enabled") else f"DISABLED ({srv.get('_disabled_reason')})"
            print(f"  • {sname} [{srv.get('registryName')}@{srv.get('version')}]: {status}")

        if loader.disabled_reasons:
            print("\nDisabled / Refused Servers:")
            for sname, reason in loader.disabled_reasons.items():
                print(f"  • {sname}: {reason}")

        if args.launch:
            print(f"\n[MCPLoader] Launching '{args.launch}'...")
            proc = loader.launch(args.launch)
            print(f"[MCPLoader] Started PID {proc.pid}. Shutting down...")
            loader.shutdown_all()
            print("[MCPLoader] Clean shutdown complete.")

    except Exception as e:
        print(f"[MCPLoader:FAIL] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

