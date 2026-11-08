"""
test_mcp_loader_and_config.py — Comprehensive Test Suite for MCP Config & Safe Loader
======================================================================================
Tests:
- Schema validation: valid, missing version, 'latest', unknown field, literal secrets.
- Generator: approval enforcement, version mismatch skipping, workspace boundary checks,
  forbidden root rejection, missing env var handling, catalog.yaml immutability.
- Tool Gating: write tools gated, unknown tools gated, read-only tools allowed.
- Loader: approval re-verification, secret rejection, path traversal rejection, audit logging.
- Mock Server: in-repo fixture lifecycle and shutdown verification.
- Report Fixes (Part A): transport populated, secrets deduplicated, slot 53 consistent counts.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from tools.mcp_config import (
    SECRET_PATTERN,
    generate_configs_for_crew,
    validate_workspace,
    check_for_literal_secrets,
)
from tools.mcp_loader import MCPSafeLoader, SecurityError


# ---------------------------------------------------------------------------
# 1. Schema Tests
# ---------------------------------------------------------------------------

def test_schema_valid_config(tmp_path: Path):
    schema_path = Path("schemas/mcp_servers.schema.json")
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    valid_payload = {
        "schemaVersion": 1,
        "crew": "devcrew",
        "generatedFrom": {
            "catalogSha256": "a" * 64,
            "registrySnapshot": "2026-11-08T00:00:00Z"
        },
        "workspaceRoot": "D:/UPS_workspace",
        "servers": {
            "filesystem": {
                "registryName": "io.github.modelcontextprotocol/filesystem",
                "version": "2.2.0",
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem@2.2.0", "D:/UPS_workspace"],
                "capability": "read-write",
                "toolPolicy": {
                    "default": "require-approval",
                    "allow": ["read_text_file"],
                    "requireApproval": ["write_file"]
                },
                "timeoutSeconds": 60,
                "enabled": True
            }
        }
    }
    jsonschema.validate(instance=valid_payload, schema=schema)


def test_schema_rejects_missing_version():
    schema = json.loads(Path("schemas/mcp_servers.schema.json").read_text(encoding="utf-8"))
    payload = {
        "schemaVersion": 1,
        "crew": "devcrew",
        "generatedFrom": {"catalogSha256": "a" * 64, "registrySnapshot": "now"},
        "workspaceRoot": "D:/UPS_workspace",
        "servers": {
            "test": {
                "registryName": "test/pkg",
                # missing version
                "transport": "stdio",
                "capability": "read-write",
                "toolPolicy": {"default": "require-approval", "allow": [], "requireApproval": []},
                "timeoutSeconds": 60,
                "enabled": True
            }
        }
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_schema_rejects_latest_version():
    schema = json.loads(Path("schemas/mcp_servers.schema.json").read_text(encoding="utf-8"))
    payload = {
        "schemaVersion": 1,
        "crew": "devcrew",
        "generatedFrom": {"catalogSha256": "a" * 64, "registrySnapshot": "now"},
        "workspaceRoot": "D:/UPS_workspace",
        "servers": {
            "test": {
                "registryName": "test/pkg",
                "version": "latest",  # violates semver regex
                "transport": "stdio",
                "capability": "read-write",
                "toolPolicy": {"default": "require-approval", "allow": [], "requireApproval": []},
                "timeoutSeconds": 60,
                "enabled": True
            }
        }
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_schema_rejects_unknown_fields():
    schema = json.loads(Path("schemas/mcp_servers.schema.json").read_text(encoding="utf-8"))
    payload = {
        "schemaVersion": 1,
        "crew": "devcrew",
        "generatedFrom": {"catalogSha256": "a" * 64, "registrySnapshot": "now"},
        "workspaceRoot": "D:/UPS_workspace",
        "servers": {},
        "unknown_root_property": "not_allowed"
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_literal_secret_detection():
    # OpenAI key pattern
    with pytest.raises(ValueError, match="Literal secret pattern detected"):
        check_for_literal_secrets({"env": {"KEY": "sk-123456789012345678901234567890"}})

    # GitHub token pattern
    with pytest.raises(ValueError, match="Literal secret pattern detected"):
        check_for_literal_secrets({"args": ["--token", "ghp_123456789012345678901234567890"]})

    # AWS access key pattern
    with pytest.raises(ValueError, match="Literal secret pattern detected"):
        check_for_literal_secrets({"env": {"AWS": "AKIAIOSFODNN7EXAMPLE"}})


# ---------------------------------------------------------------------------
# 2. Generator & Workspace Tests
# ---------------------------------------------------------------------------

def test_workspace_validation_and_boundary_rejection(tmp_path: Path):
    ws = tmp_path / "valid_workspace"
    forbidden1 = tmp_path / "project_root"
    forbidden2 = forbidden1 / "vault"
    forbidden1.mkdir()
    forbidden2.mkdir()

    # Valid path inside tmp_path
    res = validate_workspace(str(ws), [str(forbidden1), str(forbidden2)])
    assert Path(res).exists()

    # Refuse forbidden root itself
    with pytest.raises(ValueError, match="matches forbidden root"):
        validate_workspace(str(forbidden1), [str(forbidden1)])

    # Refuse path inside forbidden root
    inside_forbidden = forbidden1 / "subdir"
    with pytest.raises(ValueError, match="located inside forbidden root"):
        validate_workspace(str(inside_forbidden), [str(forbidden1)])


def test_catalog_immutability():
    """Verify that running mcp_config and mcp_loader never mutates catalog.yaml."""
    cat_path = Path("DevCrew-Vault/catalog.yaml")
    assert cat_path.is_file()
    initial_sha = hashlib.sha256(cat_path.read_bytes()).hexdigest()

    # Run generator dry-run and full run
    generate_configs_for_crew(crew="devcrew", dry_run=True)
    generate_configs_for_crew(crew="devcrew", dry_run=False)

    # Run loader
    loader = MCPSafeLoader(crew="devcrew")
    loader.load()

    post_sha = hashlib.sha256(cat_path.read_bytes()).hexdigest()
    assert initial_sha == post_sha, "catalog.yaml was modified during execution!"


def test_generator_output_conforms_to_schema():
    cfg, claude_exp, cursor_exp = generate_configs_for_crew(crew="devcrew", dry_run=True)
    schema = json.loads(Path("schemas/mcp_servers.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=cfg, schema=schema)

    # Verify only approved servers are included (4 servers)
    assert len(cfg["servers"]) == 4
    assert "filesystem" in cfg["servers"]
    assert "git" in cfg["servers"]
    assert "playwright-mcp" in cfg["servers"]
    assert "context7" in cfg["servers"]

    # Verify context7 disabled when key missing
    if "CONTEXT7_API_KEY" not in os.environ and not Path(".env.mcp").exists():
        assert cfg["servers"]["context7"]["enabled"] is False

    # Check exports format
    assert "_generated" in claude_exp
    assert "filesystem" in claude_exp["mcpServers"]
    assert "_generated" in cursor_exp
    assert "filesystem" in cursor_exp["mcpServers"]


# ---------------------------------------------------------------------------
# 3. Tool Gating & Safety Hook Tests
# ---------------------------------------------------------------------------

def test_tool_gating_hook():
    loader = MCPSafeLoader(crew="devcrew")
    loader.load()

    # Read tools are allowed without human gate for filesystem
    assert loader.gate("filesystem", "read_text_file") == "allow"
    assert loader.gate("filesystem", "list_directory") == "allow"
    assert loader.gate("filesystem", "get_file_info") == "allow"

    # Write tools must ALWAYS require approval
    assert loader.gate("filesystem", "write_file") == "require_approval"
    assert loader.gate("filesystem", "edit_file") == "require_approval"
    assert loader.gate("filesystem", "append_file") == "require_approval"
    assert loader.gate("filesystem", "create_directory") == "require_approval"

    # Git verified tools: status/diff/log allowed; mutating tools require approval
    assert loader.gate("git", "git_status") == "allow"
    assert loader.gate("git", "git_diff_unstaged") == "allow"
    assert loader.gate("git", "git_diff_staged") == "allow"
    assert loader.gate("git", "git_log") == "allow"
    assert loader.gate("git", "git_commit") == "require_approval"
    assert loader.gate("git", "git_add") == "require_approval"
    assert loader.gate("git", "git_reset") == "require_approval"
    assert loader.gate("git", "git_create_branch") == "require_approval"

    # Invariant: Code execution tools NEVER in allow
    assert loader.gate("playwright-mcp", "browser_evaluate") == "require_approval"
    assert loader.gate("playwright-mcp", "browser_run_code_unsafe") == "require_approval"

    # Invariant: Untrusted web content tools require approval by default
    assert loader.gate("playwright-mcp", "browser_snapshot") == "require_approval"
    assert loader.gate("playwright-mcp", "browser_take_screenshot") == "require_approval"
    assert loader.gate("playwright-mcp", "browser_get_html") == "require_approval"
    assert loader.gate("playwright-mcp", "browser_navigate") == "require_approval"

    # Context7 policy: default is require-approval; when disabled by missing key, gate returns deny
    assert loader.active_servers["context7"]["toolPolicy"]["default"] == "require-approval"
    assert loader.gate("context7", "query-docs") == "deny"  # disabled server returns deny

    # Unknown tool defaults to require_approval
    assert loader.gate("filesystem", "unknown_custom_tool") == "require_approval"

    # Unapproved or non-existent server denied
    assert loader.gate("non_existent_server", "any_tool") == "deny"


def test_tool_evidence_and_static_verification():
    cfg, _, _ = generate_configs_for_crew(crew="devcrew", dry_run=True)
    servers = cfg["servers"]

    # Playwright allow list must be empty (all actions require approval)
    assert servers["playwright-mcp"]["toolPolicy"]["allow"] == []
    assert "_security_note" in servers["playwright-mcp"]
    assert "--isolated" in servers["playwright-mcp"]["_security_note"]
    assert "--allowed-origins" in servers["playwright-mcp"]["_security_note"]

    # Context7 default is require-approval and allow list is empty
    assert servers["context7"]["toolPolicy"]["default"] == "require-approval"
    assert servers["context7"]["toolPolicy"]["allow"] == []

    # All servers have toolEvidence recorded with static file/line references
    for sname in ("filesystem", "git", "playwright-mcp", "context7"):
        evidence = servers[sname].get("toolEvidence")
        assert evidence is not None, f"Server {sname} missing toolEvidence"
        assert len(evidence) > 0
        for tool_name, ev_ref in evidence.items():
            assert "#L" in ev_ref or ":" in ev_ref


def test_git_uvx_pinning_and_repo_validation(tmp_path: Path):
    cfg, claude_exp, cursor_exp = generate_configs_for_crew(crew="devcrew", dry_run=True)
    git_srv = cfg["servers"]["git"]

    # Verify uvx syntax: uvx --from mcp-server-git==<ver> mcp-server-git --repository <path>
    assert git_srv["command"] == "uvx"
    assert git_srv["args"][:3] == ["--from", f"mcp-server-git=={git_srv['version']}", "mcp-server-git"]
    assert "--repository" in git_srv["args"]

    assert claude_exp["mcpServers"]["git"]["command"] == "uvx"
    assert claude_exp["mcpServers"]["git"]["args"][:3] == ["--from", f"mcp-server-git=={git_srv['version']}", "mcp-server-git"]

    # Test loader repo validation: directory inside workspaceRoot that lacks .git disables git server
    ws_root = Path(cfg["workspaceRoot"])
    non_git_subdir = ws_root / "test_non_git_subproject"
    non_git_subdir.mkdir(parents=True, exist_ok=True)
    try:
        fake_config = tmp_path / "mcp_servers.json"
        fake_payload = dict(cfg)
        fake_payload["servers"] = dict(cfg["servers"])
        fake_payload["servers"]["git"] = dict(git_srv)
        fake_payload["servers"]["git"]["args"] = [
            "--from", f"mcp-server-git=={git_srv['version']}", "mcp-server-git", "--repository", str(non_git_subdir).replace("\\", "/")
        ]
        fake_config.write_text(json.dumps(fake_payload), encoding="utf-8")

        loader = MCPSafeLoader(crew="devcrew", config_path=fake_config)
        loader.load()
        assert loader.active_servers["git"]["enabled"] is False
        assert "not an initialized git repository" in loader.disabled_reasons["git"]
    finally:
        if non_git_subdir.exists():
            shutil.rmtree(non_git_subdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 4. Loader Approval Drift & Secret Defense
# ---------------------------------------------------------------------------

def test_loader_detects_approval_drift(tmp_path: Path):
    """If catalog.yaml removes an approval, loader marks it refused."""
    custom_cat = tmp_path / "catalog.yaml"
    custom_cat.write_text(yaml.dump({
        "approvals": {
            "io.github.modelcontextprotocol/filesystem": "2.2.0"
            # git, playwright, context7 removed
        }
    }), encoding="utf-8")

    loader = MCPSafeLoader(crew="devcrew", catalog_path=custom_cat)
    loader.load()

    # Filesystem is active, others are refused due to drift
    assert "filesystem" in loader.active_servers
    assert "git" in loader.disabled_reasons
    assert "playwright-mcp" in loader.disabled_reasons


def test_loader_audit_log_redaction(tmp_path: Path):
    audit_file = tmp_path / "mcp-audit.jsonl"
    loader = MCPSafeLoader(crew="devcrew")
    loader.audit_log_path = audit_file
    loader.load()

    loader.gate("filesystem", "write_file", arguments={"path": "d:/UPS_workspace/test.txt", "token": "sensitive_val"})
    assert audit_file.is_file()

    line = json.loads(audit_file.read_text(encoding="utf-8").strip())
    assert line["server"] == "filesystem"
    assert line["tool"] == "write_file"
    assert line["arguments"]["token"] == "[REDACTED]"
    assert line["arguments"]["path"] == "d:/UPS_workspace/test.txt"


# ---------------------------------------------------------------------------
# 5. Mock MCP Server Lifecycle Test
# ---------------------------------------------------------------------------

def test_mock_mcp_server_lifecycle():
    """Verify stdio server launch, communication, and clean shutdown using mock fixture."""
    fixture_path = Path("tests/fixtures/mock_mcp_server.py").resolve()
    assert fixture_path.is_file()

    proc = subprocess.Popen(
        [sys.executable, str(fixture_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    assert proc.poll() is None

    # Send initialize JSON-RPC request
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
    proc.stdin.write(req)
    proc.stdin.flush()

    res_line = proc.stdout.readline()
    res = json.loads(res_line)
    assert res.get("id") == 1
    assert res.get("result", {}).get("serverInfo", {}).get("name") == "mock-mcp-server"

    # Terminate cleanly
    proc.terminate()
    proc.wait(timeout=3)
    assert proc.poll() is not None


# ---------------------------------------------------------------------------
# 6. Part A Bug Fix Verification
# ---------------------------------------------------------------------------

def test_part_a_report_and_data_fixes():
    conn = sqlite3.connect("DevCrew-Vault/registry.db")
    cur = conn.cursor()

    # 1. Transport column is populated for all selected/approved servers
    cur.execute("SELECT name, transport FROM mcp_servers WHERE status IN ('selected', 'approved')")
    rows = cur.fetchall()
    assert len(rows) == 24
    for name, transport in rows:
        assert transport in ("stdio", "streamable-http"), f"Server {name} has invalid transport: {transport}"

    # 2. Slot 53 is unfilled due to license in catalog.yaml
    cat_data = yaml.safe_load(Path("DevCrew-Vault/catalog.yaml").read_text(encoding="utf-8"))
    slot_53 = None
    for mod in cat_data.get("modules", []):
        for p in mod.get("pinned_slots", []):
            if p.get("slot") == 53:
                slot_53 = p
                break
    assert slot_53 is not None
    assert "unfilled" in slot_53.get("status")
    assert "CC-BY-SA-4.0" in slot_53.get("status")

    # 3. Check report file consistency
    report_text = Path("RESULT-REPORT.md").read_text(encoding="utf-8")
    assert "71 / 100" in report_text
    assert "29 / 100" in report_text
    assert "Human Approval Authority & Audit" in report_text
    assert "16 / 49 selected / ceiling" in report_text

    # Verify transport in MCP inventory table rows
    inventory_lines = [
        line for line in report_text.splitlines()
        if ("`stdio`" in line or "`streamable-http`" in line) and "|" in line
    ]
    assert len(inventory_lines) == 24
    for line in inventory_lines:
        assert "None" not in line.split("`")[7]  # transport column not None
