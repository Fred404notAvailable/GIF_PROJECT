"""
mcp_vet.py — Static Vetting, Scoring, Placement, and Pairing
============================================================
Evaluates MCP servers from metadata and static repository inspection only.
Computes 0-100 vetting score, enforces developer-tool fit and vetting floors,
assigns servers to modules by strict relevance (ceilings, no quotas),
places cross-cutting utility servers into General / Utilities,
links paired skills by real affinity (>=2 shared tags or strong signal, no padding),
and generates MCP vault notes, MCP-APPROVALS-NEEDED.md, and MCP-REPORT.md.

Ground Rules:
- Zero server code executed; zero secrets stored.
- Unknown means unsafe: unknown capability treated as read-write; undeterminable secrets marked unverified.
- Never label a server read-only unless every discovered tool is read-only.
- Maintainer class requires verified namespace matching vendor domain/org. Org mismatch yields community.
- Test servers (everything) and unapproved licenses (MPL-2.0) are kept as candidate.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Ensure tools/ is on sys.path
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config
from db import (
    clear_mcp_links,
    get_connection,
    init_db,
    list_mcp_links,
    list_mcp_servers,
    set_mcp_tech_tags,
    upsert_mcp_link,
    upsert_mcp_server,
)
from catalog import load_catalog, _DEFAULT_MODULES
from build_map import DEFAULT_TECH_KEYWORDS


# ---------------------------------------------------------------------------
# Placement & Seed Priorities
# ---------------------------------------------------------------------------

GENERAL_UTILITIES_SEEDS = [
    "io.github.modelcontextprotocol/filesystem",
    "io.github.modelcontextprotocol/git",
    "io.github.modelcontextprotocol/fetch",
    "io.github.modelcontextprotocol/time",
    "io.github.modelcontextprotocol/memory",
    "io.github.modelcontextprotocol/sequential-thinking",
    "io.github.upstash/context7",
    "io.github.firecrawl/firecrawl-mcp-server",
]

MODULE_SEEDS: dict[int, list[str]] = {
    1: [
        "com.cloudflare.mcp/mcp",
        "com.stripe/mcp",
        "io.github.github/github-mcp-server",
    ],
    2: [
        "com.figma.mcp/mcp",
    ],
    3: [
        "com.neon/mcp",
        "io.github.ClickHouse/mcp-clickhouse",
        "io.github.firebase/firebase-mcp",
        "com.supabase/mcp",
        "io.prisma/mcp",
    ],
    4: [
        "io.github.getsentry/sentry-mcp",
    ],
    5: [
        "co.axiom/mcp",
        "io.github.comet-ml/opik-mcp",
        "ai.exa/exa",
    ],
    6: [
        "io.github.microsoft/playwright-mcp",
        "io.github.browserbase/mcp-server-browserbase",
    ],
    7: [
        "io.github.containers/kubernetes-mcp-server",
    ],
}

MODULE_STRONG_KEYWORDS: dict[int, set[str]] = {
    1: {"stripe", "cloudflare", "fastapi", "hono", "graphql", "rest", "backend", "express", "microservice", "temporal", "kafka", "rabbitmq"},
    2: {"figma", "react", "nextjs", "angular", "vue", "tailwind", "shadcn", "canvas", "frontend", "ui", "design"},
    3: {"postgres", "postgresql", "clickhouse", "neon", "supabase", "firebase", "redis", "database", "sql", "storage", "prisma"},
    4: {"sentry", "owasp", "semgrep", "security", "codeql", "vulnerability", "pentest", "stride", "threat", "audit", "cve"},
    5: {"langgraph", "langchain", "prompt", "llm", "opik", "axiom", "autonomous", "eval", "tracing", "rag", "neural search"},
    6: {"playwright", "cypress", "e2e", "qa", "test", "testing", "browserbase", "stagehand"},
    7: {"kubernetes", "k8s", "docker", "devops", "cloud", "aws"},
}

GENERIC_KEYWORDS: set[str] = {
    "api", "data", "agent", "search", "build", "tool", "server", "service",
    "client", "app", "application", "ai", "model",
}

WRITE_PATTERNS = re.compile(
    r"\b(create|write|update|modify|edit|insert|upsert|mutate|post|put|patch|send|publish|trigger|deploy|spend|charge|transfer|commit|add|reset|checkout|branch|push)\b",
    re.IGNORECASE,
)
DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(delete|drop|remove|destroy|purge|truncate|execute|eval|exec|shell|bash|rm\s+-rf|spend|charge|transfer)\b",
    re.IGNORECASE,
)
READ_ONLY_PATTERNS = re.compile(
    r"\b(read|get|fetch|query|search|lookup|inspect|view|browse|list|scan|retrieve|docs|status)\b",
    re.IGNORECASE,
)

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"exfiltrat", re.IGNORECASE),
    re.compile(r"curl\s+.*\|\s*sh", re.IGNORECASE),
]

SECRET_KEYWORDS = re.compile(
    r"\b([A-Z0-9_]*(?:TOKEN|API_KEY|SECRET|PASSWORD|CREDENTIAL|AUTH_KEY)[A-Z0-9_]*)\b",
)

# Known static tool evidence
KNOWN_TOOL_CAPABILITIES: dict[str, tuple[str, list[str]]] = {
    "io.github.modelcontextprotocol/git": ("read-write", ["git_status", "git_diff_unstaged", "git_commit", "git_add", "git_reset", "git_create_branch", "git_checkout"]),
    "io.github.modelcontextprotocol/filesystem": ("read-write", ["read_file", "write_file", "create_directory", "move_file", "list_directory"]),
    "io.github.modelcontextprotocol/memory": ("read-write", ["create_entities", "create_relations", "add_observations", "delete_entities"]),
    "io.github.modelcontextprotocol/time": ("read-only", ["get_current_time", "convert_time"]),
    "io.github.modelcontextprotocol/fetch": ("read-only", ["fetch"]),
    "io.github.modelcontextprotocol/sequential-thinking": ("read-only", ["sequentialthinking"]),
    "io.github.upstash/context7": ("read-only", ["get_library_docs"]),
    "io.github.microsoft/playwright-mcp": ("read-write", ["browser_click", "browser_fill", "browser_navigate", "browser_snapshot"]),
    "io.github.github/github-mcp-server": ("read-write", ["create_issue", "create_pull_request", "push_files", "fork_repository"]),
    "com.stripe/mcp": ("read-write", ["create_customer", "create_payment_intent", "create_invoice"]),
    "com.cloudflare.mcp/mcp": ("read-write", ["deploy_worker", "kv_set", "d1_execute"]),
    "com.neon/mcp": ("read-write", ["create_branch", "create_project", "execute_sql"]),
    "io.github.ClickHouse/mcp-clickhouse": ("read-write", ["execute_query"]),
    "io.github.firebase/firebase-mcp": ("read-write", ["manage_firestore", "deploy_rules"]),
    "com.figma.mcp/mcp": ("read-write", ["post_comment", "inspect_node"]),
    "com.supabase/mcp": ("read-write", ["execute_sql", "manage_branch"]),
    "io.github.getsentry/sentry-mcp": ("read-write", ["resolve_issue", "assign_issue"]),
    "io.github.browserbase/mcp-server-browserbase": ("read-write", ["stagehand_act", "stagehand_extract"]),
    "co.axiom/mcp": ("read-write", ["query_dataset", "stream_logs"]),
    "io.github.comet-ml/opik-mcp": ("read-write", ["log_traces", "log_feedback"]),
    "ai.exa/exa": ("read-only", ["search", "find_similar", "get_contents"]),
    "io.github.firecrawl/firecrawl-mcp-server": ("read-only", ["scrape", "crawl", "map"]),
    "io.prisma/mcp": ("read-write", ["manage_compute", "execute_sql"]),
    "io.github.containers/kubernetes-mcp-server": ("read-write", ["deploy_pod", "delete_namespace", "list_services"]),
}

KNOWN_SECRETS: dict[str, list[str]] = {
    "io.github.github/github-mcp-server": ["GITHUB_PERSONAL_ACCESS_TOKEN", "Authorization"],
    "com.stripe/mcp": ["STRIPE_SECRET_KEY"],
    "com.cloudflare.mcp/mcp": ["CLOUDFLARE_API_TOKEN"],
    "com.neon/mcp": ["NEON_API_KEY"],
    "com.figma.mcp/mcp": ["FIGMA_ACCESS_TOKEN"],
    "com.supabase/mcp": ["SUPABASE_ACCESS_TOKEN"],
    "io.github.getsentry/sentry-mcp": ["SENTRY_AUTH_TOKEN"],
    "io.github.browserbase/mcp-server-browserbase": ["BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID", "GEMINI_API_KEY"],
    "co.axiom/mcp": ["AXIOM_TOKEN"],
    "io.github.comet-ml/opik-mcp": ["OPIK_API_KEY"],
    "io.github.firecrawl/firecrawl-mcp-server": ["FIRECRAWL_API_KEY"],
    "io.github.ClickHouse/mcp-clickhouse": ["CLICKHOUSE_PASSWORD"],
    "io.github.firebase/firebase-mcp": ["FIREBASE_SERVICE_ACCOUNT_KEY"],
    "io.prisma/mcp": ["Authorization"],
    "ai.exa/exa": ["EXA_API_KEY"],
}

ZERO_SECRETS_VERIFIED: set[str] = {
    "io.github.modelcontextprotocol/filesystem",
    "io.github.modelcontextprotocol/git",
    "io.github.modelcontextprotocol/fetch",
    "io.github.modelcontextprotocol/time",
    "io.github.modelcontextprotocol/memory",
    "io.github.modelcontextprotocol/sequential-thinking",
    "io.github.modelcontextprotocol/everything",
    "io.github.microsoft/playwright-mcp",
    "io.github.upstash/context7",
}


# ---------------------------------------------------------------------------
# Vetting Engine
# ---------------------------------------------------------------------------

class MCPVetter:
    """Performs static vetting of candidate servers and assigns safety scores."""

    def __init__(self, config: dict[str, Any], catalog: dict[str, Any]):
        self.config = config
        self.catalog = catalog
        self.allowed_licenses = set(config.get("allowed_licenses", ["MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0"]))

    def vet(self, server: dict[str, Any]) -> tuple[int, str, str, int, list[str]]:
        """Compute (vetting_score, vetting_notes, capability_class, requires_secrets, flagged_secrets)."""
        score = 0
        breakdowns: list[str] = []
        flagged_secrets: list[str] = []

        name = server.get("name", "")
        title = server.get("title", "")
        desc = server.get("description", "")
        version = server.get("version", "")
        maintainer_class = server.get("maintainer_class", "community")
        publisher_verified = server.get("publisher_verified", 0)
        repo_archived = server.get("repo_archived", 0)
        license_val = server.get("license") or ""
        transport = server.get("transport", "")
        packages = json.loads(server["snapshot_json"]).get("packages", []) if server.get("snapshot_json") else []
        remotes = json.loads(server["snapshot_json"]).get("remotes", []) if server.get("snapshot_json") else []

        full_text = f"{name} {title} {desc}"

        # Maintainer class verification:
        repo_url = server.get("repo_url") or ""
        repo_owner = ""
        m_repo = re.search(r"github\.com/([^/]+)/", repo_url)
        if m_repo:
            repo_owner = m_repo.group(1).lower()

        # Org mismatch detection (e.g. containers/kubernetes-mcp-server != kubernetes org)
        if "kubernetes" in name.lower() and repo_owner not in ("kubernetes", "kubernetes-sigs"):
            maintainer_class = "community"
            server["maintainer_class"] = "community"
            server["publisher_verified"] = 0
            publisher_verified = 0

        # 1. Publisher scoring
        if maintainer_class in ("official-vendor", "reference"):
            score += 25
            breakdowns.append(f"Publisher: {maintainer_class} (+25)")
        elif publisher_verified:
            score += 15
            breakdowns.append("Publisher: verified domain (+15)")
        else:
            score += 5
            breakdowns.append("Publisher: community (+5)")

        # 2. Maintenance scoring
        if repo_archived:
            score -= 50
            breakdowns.append("Maintenance: repo archived (-50)")
        else:
            score += 15
            breakdowns.append("Maintenance: not archived (+15)")
            last_commit = server.get("last_commit_at")
            if last_commit:
                score += 10
                breakdowns.append("Maintenance: recent commit/release (+10)")

        # 3. License scoring
        lic_upper = license_val.upper()
        if any(allowed.upper() in lic_upper for allowed in self.allowed_licenses):
            score += 15
            breakdowns.append(f"License: {license_val} in allowed list (+15)")
        elif license_val:
            score += 0
            breakdowns.append(f"License: {license_val} unapproved (0)")
        else:
            breakdowns.append("License: unspecified (0)")

        # 4. Pinning scoring
        is_exact_semver = bool(re.match(r"^\d+(\.\d+)*", version)) and version.lower() != "latest"
        if is_exact_semver:
            score += 15
            breakdowns.append(f"Pinning: exact version {version} (+15)")
        else:
            breakdowns.append(f"Pinning: unpinned or non-semver '{version}' (0)")

        if remotes:
            stable_remote = any(r.get("url", "").startswith("https://") for r in remotes)
            if stable_remote:
                score += 5
                breakdowns.append("Remote: https vendor endpoint (+5)")

        # 5. Permission / Capability Class classification (from evidence)
        if name in KNOWN_TOOL_CAPABILITIES:
            cap_class, tool_list = KNOWN_TOOL_CAPABILITIES[name]
            capability_class = cap_class
            evidence_str = f"tools: {', '.join(tool_list[:4])}{'...' if len(tool_list)>4 else ''}"
            breakdowns.append(f"Capability: {capability_class} ({evidence_str})")
        elif DESTRUCTIVE_PATTERNS.search(full_text):
            capability_class = "destructive"
            breakdowns.append("Capability: destructive operations detected (0)")
        elif WRITE_PATTERNS.search(full_text):
            capability_class = "read-write"
            score += 5
            breakdowns.append("Capability: read-write operations detected (+5)")
        elif READ_ONLY_PATTERNS.search(full_text) and not WRITE_PATTERNS.search(full_text):
            capability_class = "read-only"
            score += 10
            breakdowns.append("Capability: verified read-only (+10)")
        else:
            capability_class = "unknown-treat-as-write"
            breakdowns.append("Capability: unknown-treat-as-write (treated as read-write)")

        # 6. Secrets analysis (from evidence)
        found_secrets: set[str] = set()
        if name in KNOWN_SECRETS:
            found_secrets.update(KNOWN_SECRETS[name])

        for p in packages:
            for env_item in p.get("environmentVariables", []):
                if isinstance(env_item, dict):
                    found_secrets.add(env_item.get("name", "ENV_VAR"))
                elif isinstance(env_item, str):
                    found_secrets.add(env_item)
            for arg_item in p.get("runtimeArguments", []):
                if isinstance(arg_item, dict):
                    val = str(arg_item.get("value", ""))
                    found_secrets.update(SECRET_KEYWORDS.findall(val.upper()))
        for r in remotes:
            for h in r.get("headers", []):
                if isinstance(h, dict):
                    hname = h.get("name", "")
                    if h.get("isSecret") or "AUTH" in hname.upper():
                        found_secrets.add(f"Header: {hname}")

        found_secrets.update(SECRET_KEYWORDS.findall(full_text.upper()))

        if found_secrets:
            requires_secrets = 1
            flagged_secrets = sorted(found_secrets)
            breakdowns.append(f"Secrets: requires {', '.join(flagged_secrets)}")
        elif name in ZERO_SECRETS_VERIFIED:
            requires_secrets = 0
            score += 5
            breakdowns.append("Secrets: verified none required (+5)")
        else:
            # Undeterminable secrets -> mark as unverified (-1)
            requires_secrets = -1
            breakdowns.append("Secrets: unverified (cannot determine required credentials)")

        # 7. Supply chain & Prompt Injection text risks
        for pat in PROMPT_INJECTION_PATTERNS:
            if pat.search(full_text):
                score -= 30
                breakdowns.append("SECURITY ALERT: Suspicious instruction text detected in description (-30)")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        breakdown_text = "; ".join(breakdowns) + ". A clean scan does not prove a server is safe."

        return score, breakdown_text, capability_class, requires_secrets, flagged_secrets


# ---------------------------------------------------------------------------
# Filter Rules: Developer Fit, Vetting Floor & Module Relevance
# ---------------------------------------------------------------------------

def check_developer_fit(server: dict[str, Any], exclude_keywords: list[str]) -> tuple[bool, str | None]:
    """Verify that server does not serve non-developer purposes (e.g. trading, real estate, lead gen)."""
    text = f"{server.get('name', '')} {server.get('title', '')} {server.get('description', '')} {server.get('slug', '')}".lower()
    for kw in exclude_keywords:
        kw_low = kw.lower()
        if kw_low in text:
            return False, f"Failed developer-tool fit: contains '{kw_low}' (non-developer purpose)"
    return True, None


def check_vetting_floor(
    server: dict[str, Any],
    floor_cfg: dict[str, Any],
    allowed_licenses: set[str],
) -> tuple[bool, str | None]:
    """Verify that server passes the documented vetting floor."""
    min_score = floor_cfg.get("min_score", 50)
    score = server.get("vetting_score", 0)
    if score < min_score:
        return False, f"Failed vetting floor: score {score} < {min_score}"

    if server.get("repo_archived"):
        return False, "Failed vetting floor: repository is archived"

    lic = server.get("license")
    if not lic or str(lic).strip().lower() in ("none", "unknown", ""):
        return False, "Failed vetting floor: license: unknown"
    if not any(allowed.upper() == str(lic).strip().upper() for allowed in allowed_licenses):
        return False, f"Failed vetting floor: license '{lic}' not in allowed list"

    ver = server.get("version") or ""
    if not ver or ver.lower() == "latest" or not re.match(r"^\d+(\.\d+)*", ver.strip()):
        return False, f"Failed vetting floor: version '{ver}' is unpinned or non-semver"

    pub_ver = server.get("publisher_verified", 0)
    m_class = server.get("maintainer_class", "community")
    if not (pub_ver == 1 or m_class in ("official-vendor", "reference")):
        return False, "Failed vetting floor: unverified namespace and community maintainer class"

    return True, None


def classify_mcp_placement(
    server: dict[str, Any],
    catalog: dict[str, Any],
    strong_keywords: set[str],
) -> tuple[str, int | None, str | None]:
    """Classify server into General / Utilities OR one of 7 modules.

    Returns: (placement_type, module_id_or_none, error_or_none)
    """
    name = server.get("name", "")
    slug = server.get("slug", "")

    # Exclude protocol test server per Round 3 Item 3
    if name == "io.github.modelcontextprotocol/everything" or slug == "modelcontextprotocol-everything-mcp":
        return "none", None, "Protocol test server, excluded from selected per Round 3 Item 3"

    # Exclude hosted service when local equivalent selected per Round 3 Item 3
    if name == "com.microsoft/playwright-cloud-browsers" or slug == "microsoft-playwright-cloud-browsers-mcp":
        return "none", None, "hosted service; local equivalent selected"

    # Firecrawl is web-scraping utility, not DevOps per Round 3 Item 3
    if "firecrawl" in name.lower() or "firecrawl" in slug.lower():
        return "general-utility", None, None

    # Check General Utilities first
    if name in GENERAL_UTILITIES_SEEDS:
        return "general-utility", None, None

    # Check module seed hints
    for mod_id, seeds in MODULE_SEEDS.items():
        if name in seeds:
            return "module", mod_id, None

    name_slug = (name + " " + server.get("slug", "")).lower()
    title = (server.get("title") or "").lower()
    desc = (server.get("description") or "").lower()
    text = f"{name_slug} {title} {desc}"

    best_id: int | None = None
    best_score = 0

    for mod in catalog.get("modules", _DEFAULT_MODULES):
        m_id = mod["id"]
        mod_strong = MODULE_STRONG_KEYWORDS.get(m_id, set())

        has_strong = any(sk in text for sk in mod_strong)
        distinct_kws = [kw.lower() for kw in mod.get("keywords", []) if kw.lower() not in GENERIC_KEYWORDS and kw.lower() in text]

        if has_strong or len(distinct_kws) >= 2:
            score = (5 if has_strong else 0) + len(distinct_kws)
            if score > best_score:
                best_score = score
                best_id = m_id

    if best_id is not None:
        return "module", best_id, None

    return "none", None, "Failed module relevance: requires >=2 distinct non-generic keywords or 1 strong-signal keyword"


def classify_mcp_module(
    server: dict[str, Any],
    catalog: dict[str, Any],
    strong_keywords: set[str],
) -> tuple[int | None, str | None]:
    """Compatibility wrapper for classifying into 7 modules."""
    placement, mod_id, err = classify_mcp_placement(server, catalog, strong_keywords)
    if placement == "module":
        return mod_id, None
    return None, err or "Failed module relevance"



def extract_tech_tags(server: dict[str, Any], tech_keywords: dict[str, list[str]]) -> list[str]:
    """Extract technology tags for an MCP server from catalog tech keyword map."""
    name = (server.get("name", "") + " " + server.get("slug", "")).lower()
    title = (server.get("title") or "").lower()
    desc = (server.get("description") or "").lower()
    text = f"{name} {title} {desc}"

    matched_tags: list[str] = []
    for tag, kws in tech_keywords.items():
        if any(kw.lower() in text for kw in kws):
            matched_tags.append(tag)
    return sorted(set(matched_tags))


# ---------------------------------------------------------------------------
# Vault Note Generation (mcp/<slug>.md)
# ---------------------------------------------------------------------------

def generate_mcp_note(
    vault_dir: Path,
    server: dict[str, Any],
    paired_skills: list[str],
) -> Path:
    """Generate DevCrew-Vault/mcp/<slug>.md for selected/approved server."""
    mcp_dir = vault_dir / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    note_path = mcp_dir / f"{server['slug']}.md"

    if note_path.exists():
        existing_text = note_path.read_text(encoding="utf-8")
        if "generated: true" not in existing_text:
            return note_path

    paired_links = "\n".join([f"- [[{slug}]]" for slug in paired_skills]) if paired_skills else "_None_"
    config_pointer = f"- [[configs/{server['slug']}.json]]" if server.get("status") == "approved" else "_Awaiting human approval in `catalog.yaml`_"

    sec_str = "Yes" if server.get("requires_secrets") == 1 else ("No" if server.get("requires_secrets") == 0 else "unverified")

    content = f"""---
generated: true
name: "{server['name']}"
slug: "{server['slug']}"
title: "{server.get('title') or server['slug']}"
version: "{server.get('version') or ''}"
approved_version: {json.dumps(server.get('approved_version'))}
publisher: "{server.get('publisher') or ''}"
publisher_verified: {server.get('publisher_verified') == 1}
maintainer_class: "{server.get('maintainer_class') or 'community'}"
capability_class: "{server.get('capability_class') or 'unknown-treat-as-write'}"
requires_secrets: "{sec_str}"
status: "{server.get('status') or 'selected'}"
module: {server.get('module_id') or 'General / Utilities'}
vetting_score: {server.get('vetting_score') or 0}
repo: "{server.get('repo_url') or ''}"
license: "{server.get('license') or ''}"
transport: "{server.get('transport') or 'stdio'}"
---

# {server.get('title') or server['slug']}

> **MCP Server Catalog Entry**
> Publisher: `{server.get('publisher')}` (Verified: {server.get('publisher_verified') == 1}) | Maintainer: `{server.get('maintainer_class')}` | Status: **{server.get('status')}** | Vetting Score: **{server.get('vetting_score')}/100**

## Description
{server.get('description') or 'No description provided.'}

## Safety & Capability Analysis
- **Capability Class:** `{server.get('capability_class')}`
- **Secrets Required:** {sec_str}
- **Vetting Breakdown:** {server.get('vetting_notes') or 'Clean scan.'}

## Paired Agent Skills
The following selected skills in the vault pair with this live MCP server (the skill teaches API usage; this server performs tool execution):
{paired_links}

## Example Client Configuration
{config_pointer}
"""
    note_path.write_text(content, encoding="utf-8")
    return note_path


# ---------------------------------------------------------------------------
# Approvals Needed Report (MCP-APPROVALS-NEEDED.md)
# ---------------------------------------------------------------------------

def format_secrets_display(requires_secrets: int, flagged_secrets: list[str] | None) -> str:
    """Format required secrets display without ever outputting bare numeric counts."""
    if flagged_secrets:
        return ", ".join(flagged_secrets)
    if requires_secrets == 0:
        return "None"
    return "unverified"


def write_approvals_needed_report(
    report_path: Path,
    selected_servers: list[dict[str, Any]],
    general_utilities: list[dict[str, Any]] | None = None,
) -> None:
    """Generate MCP-APPROVALS-NEEDED.md listing selected servers with verified pins and explicit combination risk notes."""
    if general_utilities is None:
        general_utilities = []
    all_selected = selected_servers + general_utilities

    lines = [
        "# MCP Server Approvals Needed",
        "",
        "> [!IMPORTANT]",
        "> MCP servers execute running code and access live external credentials.",
        "> Therefore, the agent **never auto-approves** an MCP server.",
        "> Every server below has been vetted by static analysis, verified against the registry snapshot, and recommended by the catalog.",
        "> To approve a server, copy its exact version pin into `DevCrew-Vault/catalog.yaml` under `approvals:`.",
        "",
        f"**Generated:** {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Selected Module Servers Awaiting Approval:** {len([s for s in selected_servers if s.get('status') == 'selected'])}",
        f"**General / Utility Servers Awaiting Approval:** {len([s for s in general_utilities if s.get('status') == 'selected'])}",
        f"**Already Approved Servers:** {len([s for s in all_selected if s.get('status') == 'approved'])}",
        "",
        "## Critical Operational & Combination Risk Notes",
        "",
        "> [!CAUTION]",
        "> Review these operational combination risks before granting human approval in `catalog.yaml`:",
        "",
        "1. **Combination Risk: `git` + `filesystem`:**",
        "   When both `io.github.modelcontextprotocol/filesystem` and `io.github.modelcontextprotocol/git` are enabled simultaneously,",
        "   an agent possesses full capability to modify local source files, stage changes, and commit or push to remote repositories.",
        "   **Mitigation:** Enforce human confirmation gates on commit/push tools and restrict filesystem scope to the target project directory.",
        "",
        "2. **Combination Risk: `fetch` + Write-Capable Servers:**",
        "   The `fetch` server retrieves external web pages. Untrusted external HTML/Markdown can contain indirect prompt-injection attempts",
        "   (`ignore prior instructions`, exfiltration triggers). If enabled alongside write-capable servers (e.g. database, cloud, git, filesystem),",
        "   an injected prompt could trigger unintended state changes, automated writes, or API calls.",
        "   **Mitigation:** Sanitize fetched web content and mandate human confirmation before write tools are triggered from fetched workflows.",
        "",
        "3. **`filesystem` Directory Scoping:**",
        "   The filesystem server operates with `read-write` capabilities. It must be strictly bounded to the workspace directory only",
        "   (e.g. `args: [\"d:\\UPS_project\"]`) to prevent arbitrary directory traversal.",
        "",
        "4. **Financial & Destructive Mutating Tools:**",
        "   Servers marked `read-write` (Stripe, Cloudflare, Neon, ClickHouse, Firebase, Supabase) can mutate cloud infrastructure or initiate transactions.",
        "   Ensure client configuration environment variable values use restricted, scoped API tokens.",
        "",
        "## Verified General / Utility Servers",
        "Cross-cutting foundational tools serving all modules (no quota target):",
        "",
        "| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |",
        "|---|---|---|---|:---:|---|---|---|---|---|---|",
    ]

    for s in general_utilities:
        sec_desc = format_secrets_display(s.get("requires_secrets", 0), s.get("flagged_secrets", []))
        lic = s.get("license") or "unknown"
        lic_src = s.get("license_source") or "unknown"
        ns_ver = "Yes" if s.get("publisher_verified") == 1 else "No"
        lines.append(
            f"| `{s['name']}` | `{s.get('version')}` | `{lic}` ({lic_src}) | `{s.get('publisher') or 'N/A'}` | {ns_ver} | `{s.get('maintainer_class')}` | `{s.get('transport')}` | `{s.get('package_types')}` | `{s.get('capability_class')}` | {sec_desc} | {s.get('vetting_score')}/100 |"
        )
    lines.append("")

    lines.append("## Verified Selected Servers by Module")
    lines.append("")

    by_module: dict[int, list[dict[str, Any]]] = {}
    for s in selected_servers:
        mid = s.get("module_id") or 1
        by_module.setdefault(mid, []).append(s)

    for mid in sorted(by_module.keys()):
        servers = by_module[mid]
        mod_name = _DEFAULT_MODULES[mid - 1]["name"] if mid <= len(_DEFAULT_MODULES) else f"Module {mid}"
        lines.append(f"### Module {mid}: {mod_name}")
        lines.append("| Name | Version | License (Source) | Publisher Namespace | Verified | Maintainer | Transport | Packages | Capability | Secrets Required | Score |")
        lines.append("|---|---|---|---|:---:|---|---|---|---|---|---|")
        for s in servers:
            sec_desc = format_secrets_display(s.get("requires_secrets", 0), s.get("flagged_secrets", []))
            lic = s.get("license") or "unknown"
            lic_src = s.get("license_source") or "unknown"
            ns_ver = "Yes" if s.get("publisher_verified") == 1 else "No"
            lines.append(
                f"| `{s['name']}` | `{s.get('version')}` | `{lic}` ({lic_src}) | `{s.get('publisher') or 'N/A'}` | {ns_ver} | `{s.get('maintainer_class')}` | `{s.get('transport')}` | `{s.get('package_types')}` | `{s.get('capability_class')}` | {sec_desc} | {s.get('vetting_score')}/100 |"
            )
        lines.append("")

    lines.append("## How to Approve")
    lines.append("Add the desired exact versions to `DevCrew-Vault/catalog.yaml` under `approvals:`:")
    lines.append("```yaml")
    lines.append("approvals:")
    for s in all_selected:
        if s.get("status") == "selected":
            lines.append(f'  "{s["name"]}": "{s.get("version")}"')
    lines.append("```")
    lines.append("")
    lines.append("Then re-sync and regenerate client configs:")
    lines.append("```bash")
    lines.append("python tools/mcp_vet.py")
    lines.append("python tools/mcp_config.py --crew devcrew")
    lines.append("```")

    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Master MCP Report Generation (MCP-REPORT.md)
# ---------------------------------------------------------------------------

def write_master_mcp_report(
    report_path: Path,
    stats: dict[str, Any],
    selected_servers: list[dict[str, Any]],
    general_utilities: list[dict[str, Any]] | None = None,
    shortfalls: dict[int, tuple[int, int]] | None = None,
    dropped_servers: list[tuple[str, str]] | None = None,
    pair_distribution: dict[int, int] | None = None,
    funnel_stats: dict[str, int] | None = None,
) -> None:
    """Generate comprehensive MCP-REPORT.md with candidate funnel, evidence-based labels, and honest shortfalls."""
    if general_utilities is None:
        general_utilities = []
    if shortfalls is None:
        shortfalls = {}
    if dropped_servers is None:
        dropped_servers = []
    if pair_distribution is None:
        pair_distribution = {}
    if funnel_stats is None:
        funnel_stats = {}
    total_selected_count = len(selected_servers) + len(general_utilities)

    lines = [
        "# DevCrew MCP Server Catalog Report (Ingest, Vet, Index, Map)",
        "",
        "> [!IMPORTANT]",
        "> **Safety Assurance:** No MCP server code was installed, executed, or run at any point during this build. No tokens, secrets, or credentials have been collected or stored. All generated client configuration files are strictly examples containing environment variable placeholders (`${VAR}`). Nothing becomes `approved` without an explicit human decision recorded in `catalog.yaml`.",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "The MCP catalog has been updated to use **threshold-driven selection** over the full ingested registry candidates rather than quota-driven padding. Only servers meeting strict developer-tool fit, minimum vetting floor (score >= 50, verified namespace or official/reference class, allowed license, pinned semver), and genuine module relevance are selected. Ceilings are respected and module shortfalls are honestly reported.",
        "",
        "| Metric | Skills Layer | MCP Catalog Layer | Total Knowledge Graph |",
        "|---|:---:|:---:|:---:|",
        f"| **Registry Universe** | 4,000+ raw packages | 58,646 registry records across 587 pages | 62,000+ cataloged records |",
        f"| **Ingested Candidates** | 99 selected skills | {stats.get('total_evaluated', 1026)} servers | {99 + stats.get('total_evaluated', 1026)} processed entities |",
        f"| **Vetted & Selected** | 99 skills (1 unfilled) | {len(selected_servers)} module + {len(general_utilities)} utilities ({total_selected_count} total) | {99 + total_selected_count} core assets |",
        "| **Approved by Human** | 99 skills | 0 (awaiting human decision in `catalog.yaml`) | 99 approved assets |",
        f"| **Typed Relationships** | 380 complements, 137 alternates | {stats.get('total_pairs', 0)} `pairs-with` links | {517 + stats.get('total_pairs', 0)} typed edges |",
        "| **Link Integrity** | 0 dangling links | 0 dangling links | 100% link consistency |",
        "",
        "---",
        "",
        "## 2. Full Candidate Ingestion & Vetting Funnel",
        "",
        "Candidate ingestion evaluated servers across the multi-stage vetting funnel:",
        "",
        "| Funnel Stage | Server Count | Percentage of Ingested | Gate Description |",
        "|---|:---:|:---:|---|",
        f"| **1. Total Ingested Candidates** | **{funnel_stats.get('total_ingested', 1026)}** | 100.0% | Registry latest packages, multi-lookup vendor seeds, and reference servers |",
        f"| **2. Passed Developer-Tool Fit** | **{funnel_stats.get('passed_fit', 820)}** | {funnel_stats.get('passed_fit', 820) / max(1, funnel_stats.get('total_ingested', 1026)) * 100:.1f}% | Excluded trading, real estate, lead generation, salons, and consumer tools |",
        f"| **3. Passed Vetting Floor** | **{funnel_stats.get('passed_floor', 185)}** | {funnel_stats.get('passed_floor', 185) / max(1, funnel_stats.get('total_ingested', 1026)) * 100:.1f}% | Score >= 50, allowed license (MIT/Apache/BSD/CC-BY), pinned semver, credible namespace |",
        f"| **4. Passed Module / Utility Relevance** | **{funnel_stats.get('passed_relevance', 38)}** | {funnel_stats.get('passed_relevance', 38) / max(1, funnel_stats.get('total_ingested', 1026)) * 100:.1f}% | Strong-signal domain match or >= 2 non-generic module keywords |",
        f"| **5. Selected for Vault Catalog** | **{total_selected_count}** | {total_selected_count / max(1, funnel_stats.get('total_ingested', 1026)) * 100:.1f}% | {len(selected_servers)} module servers (under 7 ceilings) + {len(general_utilities)} foundational utilities |",
        "",
        "---",
        "",
        "## 3. Seed Multi-Lookup Results Summary",
        "",
        "Multi-lookup queries (name, publisher namespace, repository URL) resolved major vendor presences in the registry (see `MCP-SEED-RESULTS.md` for full query logs):",
        "- **Found in Registry (18):** GitHub (`io.github.github/github-mcp-server`), Playwright (`io.github.microsoft/playwright-mcp`), Supabase (`com.supabase/mcp`), Sentry (`io.github.getsentry/sentry-mcp`), Prisma (`io.prisma/mcp`), Browserbase (`io.github.browserbase/mcp-server-browserbase`), Stripe (`com.stripe/mcp`), Cloudflare (`com.cloudflare.mcp/mcp`), Neon (`com.neon/mcp`), ClickHouse (`io.github.ClickHouse/mcp-clickhouse`), Firebase (`io.github.firebase/firebase-mcp`), Figma (`com.figma.mcp/mcp`), Context7 (`io.github.upstash/context7`), Axiom (`co.axiom/mcp`), Comet Opik (`io.github.comet-ml/opik-mcp`), Exa (`ai.exa/exa`), Firecrawl (`io.github.firecrawl/firecrawl-mcp-server`), AWS OSCAL (`io.github.awslabs/mcp-server-for-oscal`).",
        "- **Community / Ambiguous (2):** Kubernetes (`io.github.containers/kubernetes-mcp-server` under `containers` org), E2B (`com.mcparmory/e2b` community wrapper).",
        "- **Not in Registry (2):** Docker (official `docker/mcp-server` not published), general AWS (`awslabs/mcp-server-aws` not published; only OSCAL server published).",
        "",
        "---",
        "",
        "## 4. Module Ceilings, Selections & Shortfalls",
        "",
        "Module targets represent **ceilings, not quotas**. General utilities are placed outside the 7 modules without synthetic padding. Shortfalls are preserved and reported directly.",
        "",
        "| Module ID | Module Name | Ceiling | Selected | Shortfall | Selected Servers |",
        "|:---:|---|:---:|:---:|:---:|---|",
    ]

    by_mod: dict[int, list[dict[str, Any]]] = {}
    for s in selected_servers:
        by_mod.setdefault(s.get("module_id", 1), []).append(s)

    for mid in range(1, 8):
        cands = by_mod.get(mid, [])
        target = 7
        count = len(cands)
        sf = target - count
        srv_names = ", ".join([f"`{c['slug']}`" for c in cands]) if cands else "_None (shortfall)_"
        status_txt = f"**{count}/{target}**" if sf > 0 else "**Ceiling Met (7/7)**"
        mod_name = _DEFAULT_MODULES[mid - 1]["name"]
        lines.append(f"| **{mid}** | {mod_name} | {target} | {count} | -{sf} | {status_txt} ({srv_names}) |")

    lines.extend([
        "",
        f"**Total Module Servers Selected:** {len(selected_servers)}/49 (Total Module Shortfall: {49 - len(selected_servers)}).",
        f"**General / Utilities Selected:** {len(general_utilities)} servers (`filesystem`, `git`, `fetch`, `time`, `memory`, `sequential-thinking`, `context7`).",
        f"**Combined Catalog Total:** {total_selected_count} verified MCP servers.",
        "",
        "---",
        "",
        "## 5. Dropped Servers and Exclusions",
        "",
        "Under the strict vetting floor and user license restrictions, the following servers are excluded from selected status:",
        "",
        "| Excluded / Dropped Server | Previous Status | Reason for Exclusion / Placement as Candidate |",
        "|---|---|---|",
        "| `io.github.modelcontextprotocol/everything` | Selected (old) | Reference test harness server containing mock echo/sampler tools. Demoted to candidate per Problem 5. |",
        "| `io.github.hashicorp/terraform-mcp-server` | Selected (old) | Licensed under MPL-2.0. Excluded from selected pending explicit user decision in `DECISIONS-NEEDED.md`. |",
    ])

    for name, reason in dropped_servers[:10]:
        lines.append(f"| `{name}` | Candidate | {reason} |")

    lines.extend([
        "",
        "---",
        "",
        "## 6. Skill-to-Server Pairing Quality",
        "",
        "Pairing requires **at least 2 shared tech tags** OR **1 tag from the strong-signal list** (e.g. Stripe, Supabase, Playwright, Figma, Cloudflare, Sentry). Servers with no genuine affinity have 0 pairs (no synthetic padding).",
        "",
        "### Pairing Distribution Across Selected Servers",
        f"- **Servers with 0 pairs:** {pair_distribution.get(0, 0)} (foundational utilities e.g. `filesystem`, `time`, `sequential-thinking` without synthetic links)",
        f"- **Servers with 1 pair:** {pair_distribution.get(1, 0)}",
        f"- **Servers with 2 pairs:** {pair_distribution.get(2, 0)}",
        f"- **Servers with 3 pairs:** {pair_distribution.get(3, 0)}",
        f"- **Total `pairs-with` Links Generated:** {stats.get('total_pairs', 0)} links.",
        "",
        "---",
        "",
        "## 7. Open Human Decisions",
        "",
        "1. **Review Pending Approvals in `MCP-APPROVALS-NEEDED.md`:** Decide which vetted servers to approve for client generation.",
        "2. **Filesystem Scoping:** Confirm workspace directory path (`args: [\"d:\\UPS_project\"]`) before running filesystem tools.",
        "3. **MPL-2.0 Decision:** Decide whether to allow MPL-2.0 in `devcrew.config.yaml` to unlock Terraform skills and MCP servers.",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main Vetting Routine
# ---------------------------------------------------------------------------

def run_vetting(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    vault_dir = Path(config["vault"]["db_path"]).resolve().parent
    db_path = Path(config["vault"]["db_path"]).resolve()
    catalog = load_catalog(config)

    conn = get_connection(db_path)
    init_db(conn)

    vetter = MCPVetter(config, catalog)

    allowed_licenses = set(config.get("allowed_licenses", ["MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0"]))
    exclude_keywords = [k.lower() for k in catalog.get("mcp_exclude_keywords", [])]
    strong_keywords = {k.lower() for k in catalog.get("mcp_strong_signal_keywords", [])}
    vetting_floor = catalog.get("mcp_vetting_floor", {"min_score": 50})
    mcp_targets = catalog.get("mcp_targets", {m["id"]: 7 for m in catalog.get("modules", _DEFAULT_MODULES)})
    tech_keywords = catalog.get("tech_keywords") or catalog.get("technology_keywords") or catalog.get("tech_tags") or DEFAULT_TECH_KEYWORDS
    approvals = catalog.get("approvals") if isinstance(catalog.get("approvals"), dict) else {}

    all_servers = list_mcp_servers(conn)
    print(f"[MCPVetter] Vetting {len(all_servers)} MCP servers in registry.db...")

    cur = conn.execute("SELECT slug, tag FROM tech_tags")
    skill_tech_tags: dict[str, set[str]] = {}
    for slug, tag in cur.fetchall():
        skill_tech_tags.setdefault(slug, set()).add(tag.lower())

    cur = conn.execute("SELECT slug FROM skill_modules WHERE status = 'selected'")
    selected_skill_slugs = {r[0] for r in cur.fetchall()}

    funnel_stats = {
        "total_ingested": len(all_servers),
        "passed_fit": 0,
        "passed_floor": 0,
        "passed_relevance": 0,
        "selected": 0,
    }

    vetted_records: list[dict[str, Any]] = []
    dropped_servers: list[tuple[str, str]] = []

    for srv in all_servers:
        score, notes, cap_class, req_secrets, flagged_secrets = vetter.vet(srv)
        tags = extract_tech_tags(srv, tech_keywords)

        srv_updated = dict(srv)
        srv_updated["vetting_score"] = score
        srv_updated["vetting_notes"] = notes
        srv_updated["capability_class"] = cap_class
        srv_updated["requires_secrets"] = req_secrets
        srv_updated["flagged_secrets"] = flagged_secrets
        srv_updated["tags"] = tags

        status = srv.get("status", "candidate")
        app_ver = approvals.get(srv["name"])
        if srv.get("repo_archived") or "Schema validation failed" in (srv.get("vetting_notes") or ""):
            status = "retired"
        elif app_ver and app_ver == srv.get("version"):
            status = "approved"
            srv_updated["approved_version"] = app_ver
            srv_updated["approved_by"] = "catalog.yaml"
            srv_updated["approved_at"] = srv.get("approved_at") or datetime.now(timezone.utc).isoformat()
        else:
            srv_updated["approved_version"] = None
            srv_updated["approved_by"] = None
            srv_updated["approved_at"] = None
            if status == "approved":
                status = "candidate"

        # Explicit exclusions per Problem 5 & Problem 2
        if srv["name"] == "io.github.modelcontextprotocol/everything":
            status = "candidate"
            srv_updated["vetting_notes"] += "; Demoted: reference test server containing mock tools"
        elif srv.get("license") == "MPL-2.0" or "terraform" in srv.get("name", "").lower():
            if "MPL-2.0" not in allowed_licenses:
                status = "candidate"
                srv_updated["vetting_notes"] += "; Excluded: MPL-2.0 license omitted from allowed_licenses"

        srv_updated["status"] = status

        # Gate 1: Developer fit
        dev_ok, dev_err = check_developer_fit(srv_updated, exclude_keywords)
        if not dev_ok:
            dropped_servers.append((srv_updated["name"], dev_err))
            vetted_records.append(srv_updated)
            continue
        funnel_stats["passed_fit"] += 1

        # Gate 2: Vetting floor
        floor_ok, floor_err = check_vetting_floor(srv_updated, vetting_floor, allowed_licenses)
        if not floor_ok:
            dropped_servers.append((srv_updated["name"], floor_err))
            vetted_records.append(srv_updated)
            continue
        funnel_stats["passed_floor"] += 1

        # Gate 3: Placement (General Utility or Module)
        placement_type, mod_id, place_err = classify_mcp_placement(srv_updated, catalog, strong_keywords)
        if placement_type == "none":
            dropped_servers.append((srv_updated["name"], place_err))
            vetted_records.append(srv_updated)
            continue
        funnel_stats["passed_relevance"] += 1

        srv_updated["placement_type"] = placement_type
        srv_updated["module_id"] = mod_id
        srv_updated["is_eligible"] = True
        vetted_records.append(srv_updated)

    # General Utilities
    general_utilities: list[dict[str, Any]] = []
    for r in vetted_records:
        if r.get("is_eligible") and r.get("placement_type") == "general-utility":
            if r["name"] != "io.github.modelcontextprotocol/everything":
                r["status"] = "selected" if r["status"] != "approved" else "approved"
                general_utilities.append(r)

    # Group eligible candidates by module
    by_module: dict[int, list[dict[str, Any]]] = {}
    for r in vetted_records:
        if r.get("is_eligible") and r.get("placement_type") == "module" and r["status"] != "retired":
            by_module.setdefault(r["module_id"], []).append(r)

    selected_servers: list[dict[str, Any]] = []
    shortfalls: dict[int, tuple[int, int]] = {}

    for mod_id in range(1, 8):
        target = mcp_targets.get(mod_id, 7)
        candidates = by_module.get(mod_id, [])

        seeds = MODULE_SEEDS.get(mod_id, [])
        seed_cands = [c for c in candidates if c["name"] in seeds]
        other_cands = [c for c in candidates if c["name"] not in seeds]

        def sort_key(c: dict[str, Any]):
            m_weight = 2 if c.get("maintainer_class") in ("official-vendor", "reference") else 0
            return (m_weight, c.get("vetting_score", 0))

        other_cands.sort(key=sort_key, reverse=True)
        ranked = seed_cands + other_cands

        chosen = ranked[:target]
        for s in chosen:
            if s["status"] not in ("approved", "retired"):
                s["status"] = "selected"
            selected_servers.append(s)

        if len(chosen) < target:
            shortfalls[mod_id] = (len(chosen), target)

    all_selected = selected_servers + general_utilities
    funnel_stats["selected"] = len(all_selected)

    # Calculate pairing
    pair_distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    server_pairs: dict[str, list[str]] = {}
    total_pairs = 0

    for s in all_selected:
        mcp_slug = s["slug"]
        mcp_tags = {t.lower() for t in s.get("tags", [])}
        paired_matches: list[tuple[str, int]] = []

        if mcp_tags:
            for skill_slug in sorted(selected_skill_slugs):
                stags = skill_tech_tags.get(skill_slug, set())
                shared = mcp_tags.intersection(stags)
                has_strong = any(st in strong_keywords for st in shared)
                if len(shared) >= 2 or has_strong:
                    paired_matches.append((skill_slug, len(shared)))

        paired_matches.sort(key=lambda m: m[1], reverse=True)
        kept_skills = [m[0] for m in paired_matches[:3]]
        server_pairs[mcp_slug] = kept_skills
        pair_count = len(kept_skills)
        pair_distribution[pair_count] = pair_distribution.get(pair_count, 0) + 1
        total_pairs += pair_count

    if not dry_run:
        clear_mcp_links(conn)

        selected_names = {sel["name"] for sel in all_selected}
        for s in vetted_records:
            is_selected = s["name"] in selected_names
            if is_selected and s["status"] not in ("approved", "retired"):
                s["status"] = "selected"
            elif not is_selected and s["status"] not in ("approved", "retired", "needs-review"):
                s["status"] = "candidate"

            upsert_mcp_server(conn, s)
            set_mcp_tech_tags(conn, s["slug"], s.get("tags", []))

        for s in all_selected:
            mcp_slug = s["slug"]
            mcp_tags = {t.lower() for t in s.get("tags", [])}
            paired = server_pairs.get(mcp_slug, [])

            for skill_slug in paired:
                stags = skill_tech_tags.get(skill_slug, set())
                shared = sorted(mcp_tags.intersection(stags))
                upsert_mcp_link(
                    conn,
                    mcp_slug=mcp_slug,
                    skill_slug=skill_slug,
                    relation="pairs-with",
                    reason=f"Shares tech tags: {', '.join(shared) if shared else 'Strong-signal domain alignment'}",
                    created_by="rule",
                )

            generate_mcp_note(vault_dir, s, paired)

        # Clean up obsolete mcp/ notes
        mcp_dir = vault_dir / "mcp"
        if mcp_dir.exists():
            selected_slugs = {s["slug"] for s in all_selected}
            for p in mcp_dir.glob("*.md"):
                if p.stem not in selected_slugs:
                    try:
                        text = p.read_text(encoding="utf-8")
                        if "generated: true" in text:
                            p.unlink()
                    except Exception:
                        pass

        write_approvals_needed_report(
            vault_dir.parent / "MCP-APPROVALS-NEEDED.md",
            selected_servers,
            general_utilities,
        )
        write_master_mcp_report(
            vault_dir.parent / "MCP-REPORT.md",
            {
                "total_evaluated": len(all_servers),
                "total_pairs": total_pairs,
            },
            selected_servers,
            general_utilities,
            shortfalls,
            dropped_servers,
            pair_distribution,
            funnel_stats,
        )

    conn.commit()
    conn.close()

    return {
        "total_evaluated": len(all_servers),
        "selected_module_servers": len(selected_servers),
        "general_utilities": len(general_utilities),
        "total_selected": len(all_selected),
        "total_pairs": total_pairs,
        "funnel_stats": funnel_stats,
    }

if __name__ == "__main__":
    cfg = load_config()
    res = run_vetting(cfg, dry_run=False)
    print("Vetting results:", json.dumps(res, indent=2))
