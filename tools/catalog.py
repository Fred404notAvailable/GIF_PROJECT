"""
catalog.py — DevCrew AI Skill Vault
=====================================
Module classification, ranking, deduplication, and coverage reporting.

Manages:
- Loading/saving ``DevCrew-Vault/catalog.yaml``
- Classifying skills into one of 7 modules by keyword scoring
- Ranking and selecting skills per module (pinned slots → alternates → candidates)
- Deduplication across sources
- Syncing the ``skill_modules`` SQLite table
- Generating ``coverage-report.md``

CLI (via watcher.py):
    python tools/watcher.py modules            # counts per module
    python tools/watcher.py module <id>        # list skills in module
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Ensure tools/ on path
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from db import (  # noqa: E402
    delete_skill_module,
    get_connection,
    init_db,
    list_skill_modules,
    list_skills,
    module_counts,
    upsert_skill_module,
)
from config import load_config  # noqa: E402

# ---------------------------------------------------------------------------
# Module definitions (fallback if catalog.yaml doesn't exist yet)
# ---------------------------------------------------------------------------

_DEFAULT_MODULES: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "Modern Backend & API Development",
        "target": 15,
        "keywords": [
            "backend", "api", "rest", "graphql", "grpc", "fastapi", "node", "nodejs",
            "express", "hono", "cloudflare", "stripe", "auth", "microservice",
            "event-driven", "event-store", "temporal", "workflow", "dotnet", ".net",
            "architecture", "clean architecture", "ddd", "hexagonal",
        ],
        "alternates": [
            "senior-backend", "nestjs-clean-typescript", "graphql-development",
            "grpc-development", "spring-boot", "convex", "database-design",
            "nodejs-best-practices", "api-design", "api-patterns",
        ],
    },
    {
        "id": 2,
        "name": "Frontend & UI Engine Frameworks",
        "target": 15,
        "keywords": [
            "frontend", "ui", "react", "next", "nextjs", "tailwind", "svelte",
            "angular", "vue", "react native", "shadcn", "storybook", "component",
            "web", "html", "css", "typescript", "javascript", "animation",
        ],
        "alternates": [
            "theme-factory", "canvas-design", "structured-logging", "t3-env-validation",
            "tailwind-v4", "shadcn-svelte", "accessibility-a11y", "web-ui-shadcn-ui",
            "web-styling-tailwind", "web-tooling-storybook",
        ],
    },
    {
        "id": 3,
        "name": "Database, Vector & Storage Management",
        "target": 15,
        "keywords": [
            "database", "db", "sql", "postgres", "postgresql", "supabase", "neon",
            "prisma", "firebase", "redis", "clickhouse", "vector", "embedding",
            "similarity", "search", "migration", "schema", "storage",
        ],
        "alternates": [
            "prisma-upgrade-v7", "neon-postgres-egress-optimizer", "claimable-postgres",
            "infra-postgres", "chdb-sql", "clickhouse-architecture-advisor",
            "database-schema-design", "vector-database-ops", "prisma-postgres",
            "prisma-database-setup",
        ],
    },
    {
        "id": 4,
        "name": "Security, Auditing & SecOps",
        "target": 15,
        "keywords": [
            "security", "audit", "owasp", "cwe", "cvss", "semgrep", "codeql",
            "sarif", "vulnerability", "exploit", "penetration", "pentest", "secops",
            "supply chain", "agentic", "injection", "csrf", "xss", "sqli",
        ],
        "alternates": [
            "fp-check", "semgrep-rule-creator", "entry-point-analyzer",
            "testing-handbook-skills", "yara-authoring", "static-analysis",
            "skills-security-audit", "security-audit", "solidity-security",
            "api-security", "api-security-testing", "api-audit",
        ],
    },
    {
        "id": 5,
        "name": "AI Architecture, LLM & Prompt Engineering",
        "target": 15,
        "keywords": [
            "ai", "llm", "prompt", "langchain", "langgraph", "rag", "agent",
            "memory", "autonomous", "context", "embedding", "vector", "openai",
            "anthropic", "evaluation", "langfuse", "observability", "deep agent",
        ],
        "alternates": [
            "langgraph", "rag-engineer", "prompt-engineer", "crewai", "memory-systems",
            "langchain-dependencies", "eskill", "deepagents-python-quickstart",
            "langgraph-python-quickstart", "langgraph-decision-models",
        ],
    },
    {
        "id": 6,
        "name": "Testing, QA & Reliability Engineering",
        "target": 10,
        "keywords": [
            "test", "testing", "tdd", "bdd", "playwright", "cypress", "jest",
            "vitest", "k6", "locust", "qa", "quality", "reliability", "debug",
            "debugging", "e2e", "unit test", "integration test",
        ],
        "alternates": [
            "receiving-code-review", "dispatching-parallel-agents",
            "temporal-python-testing", "webapp-testing", "production-code-audit",
            "jest", "cypress", "playwright", "api-testing-observability-api-mock",
        ],
    },
    {
        "id": 7,
        "name": "DevOps, Containers & Cloud Automation",
        "target": 15,
        "keywords": [
            "devops", "docker", "kubernetes", "k8s", "terraform", "ansible",
            "helm", "ci", "cd", "github actions", "aws", "azure", "gcp",
            "cloud", "deploy", "deployment", "container", "infrastructure",
        ],
        "alternates": [
            "terraform-skill", "aws-serverless", "azure-devops",
            "observability-engineer", "cloudflare", "docker-compose-patterns",
            "docker-build-strategies", "aws-serverless-eda", "aws-cdk-development",
            "infra-ci-cd-github-actions", "devops-deploy",
        ],
    },
]

# ---------------------------------------------------------------------------
# Pinned slots from the phase-2 prompt Task 1c
# ---------------------------------------------------------------------------

_PINNED_SLOTS: list[dict[str, Any]] = [
    # Module 1
    {"slot": 1,  "module_id": 1, "slug": "api-design-principles",         "source": "wshobson-agents"},
    {"slot": 2,  "module_id": 1, "slug": "architecture-patterns",         "source": "wshobson-agents"},
    {"slot": 3,  "module_id": 1, "slug": "microservices-patterns",        "source": "wshobson-agents"},
    {"slot": 4,  "module_id": 1, "slug": "dotnet-backend-patterns",       "source": "wshobson-agents"},
    {"slot": 5,  "module_id": 1, "slug": "nodejs-backend-patterns",       "source": "wshobson-agents"},
    {"slot": 6,  "module_id": 1, "slug": "fastapi-templates",             "source": "wshobson-agents"},
    {"slot": 7,  "module_id": 1, "slug": "workflow-orchestration-patterns","source": "wshobson-agents"},
    {"slot": 8,  "module_id": 1, "slug": "event-store-design",            "source": "wshobson-agents"},
    {"slot": 9,  "module_id": 1, "slug": "hono",                          "source": "hono"},
    {"slot": 10, "module_id": 1, "slug": "cloudflare",                    "source": "cloudflare"},
    {"slot": 11, "module_id": 1, "slug": "better-auth-best-practices",    "source": "better-auth"},
    {"slot": 12, "module_id": 1, "slug": "better-auth-security-best-practices", "source": "better-auth"},
    {"slot": 13, "module_id": 1, "slug": "stripe-best-practices",         "source": "stripe"},
    {"slot": 14, "module_id": 1, "slug": "mcp-builder",                   "source": "anthropic-skills"},
    {"slot": 15, "module_id": 1, "slug": "backend-development",           "source": "claudekit"},
    # Module 2
    {"slot": 16, "module_id": 2, "slug": "frontend-design",               "source": "anthropic-skills"},
    {"slot": 17, "module_id": 2, "slug": "web-artifacts-builder",         "source": "anthropic-skills"},
    {"slot": 18, "module_id": 2, "slug": "react-best-practices",          "source": "vercel-agent-skills"},
    {"slot": 19, "module_id": 2, "slug": "next-dev-loop",                 "source": "nextjs-official"},
    {"slot": 20, "module_id": 2, "slug": "tailwind-design-system",        "source": "wshobson-agents"},
    {"slot": 21, "module_id": 2, "slug": "react-native-best-practices",   "source": "callstack-rn"},
    {"slot": 22, "module_id": 2, "slug": "frontend-patterns",             "source": "everything-claude-code"},
    {"slot": 23, "module_id": 2, "slug": "web-ui-shadcn-ui",              "source": "agents-inc"},
    {"slot": 24, "module_id": 2, "slug": "angular-best-practices",        "source": "antigravity-awesome"},
    {"slot": 25, "module_id": 2, "slug": "server-actions",                "source": "szum-tech"},
    {"slot": 26, "module_id": 2, "slug": "react-19-compiler",             "source": "szum-tech"},
    {"slot": 27, "module_id": 2, "slug": "tailwind-css-4",                "source": "szum-tech"},
    {"slot": 28, "module_id": 2, "slug": "storybook-testing",             "source": "szum-tech"},
    {"slot": 29, "module_id": 2, "slug": "svelte",                        "source": "modernstack"},
    {"slot": 30, "module_id": 2, "slug": "ui-visual-validator",           "source": "antigravity-awesome"},
    # Module 3
    {"slot": 31, "module_id": 3, "slug": "supabase-postgres-best-practices", "source": "supabase"},
    {"slot": 32, "module_id": 3, "slug": "supabase",                      "source": "supabase"},
    {"slot": 33, "module_id": 3, "slug": "neon-postgres",                 "source": "neon"},
    {"slot": 34, "module_id": 3, "slug": "neon-postgres-branches",        "source": "neon"},
    {"slot": 35, "module_id": 3, "slug": "prisma-postgres-setup",         "source": "prisma"},
    {"slot": 36, "module_id": 3, "slug": "prisma-cli",                    "source": "prisma"},
    {"slot": 37, "module_id": 3, "slug": "firebase-basics",               "source": "firebase"},
    {"slot": 38, "module_id": 3, "slug": "sql-optimization-patterns",     "source": "wshobson-agents"},
    {"slot": 39, "module_id": 3, "slug": "database-migration",            "source": "wshobson-agents"},
    {"slot": 40, "module_id": 3, "slug": "postgresql-table-design",       "source": "wshobson-agents"},
    {"slot": 41, "module_id": 3, "slug": "clickhouse-best-practices",     "source": "clickhouse"},
    {"slot": 42, "module_id": 3, "slug": "vector-index-tuning",           "source": "wshobson-agents"},
    {"slot": 43, "module_id": 3, "slug": "similarity-search-patterns",    "source": "wshobson-agents"},
    {"slot": 44, "module_id": 3, "slug": "hybrid-search-implementation",  "source": "wshobson-agents"},
    {"slot": 45, "module_id": 3, "slug": "embedding-strategies",          "source": "wshobson-agents"},
    # Module 4
    {"slot": 46, "module_id": 4, "slug": "security-audit",                "source": "netresearch-security"},
    {"slot": 47, "module_id": 4, "slug": "secure-webapp",                 "source": "secure-webapp"},
    {"slot": 48, "module_id": 4, "slug": "shared-security-auth-security", "source": "agents-inc"},
    {"slot": 49, "module_id": 4, "slug": "codeql",                        "source": "awesome-copilot"},
    {"slot": 50, "module_id": 4, "slug": "semgrep-rule-creator",          "source": "antigravity-awesome"},
    {"slot": 51, "module_id": 4, "slug": "stride-analysis-patterns",      "source": "antigravity-awesome"},
    {"slot": 52, "module_id": 4, "slug": "firebase-security-rules-auditor","source": "firebase"},
    {"slot": 53, "module_id": 4, "slug": "api-security",                  "source": "antigravity-awesome"},
    {"slot": 54, "module_id": 4, "slug": "api-security-testing",          "source": "antigravity-awesome"},
    {"slot": 55, "module_id": 4, "slug": "security-auditor",              "source": "antigravity-awesome"},
    {"slot": 56, "module_id": 4, "slug": "security-review",               "source": "awesome-copilot"},
    {"slot": 57, "module_id": 4, "slug": "vulnerability-scanner",         "source": "antigravity-awesome"},
    {"slot": 58, "module_id": 4, "slug": "web-security-testing",          "source": "antigravity-awesome"},
    {"slot": 59, "module_id": 4, "slug": "xss-html-injection",            "source": "antigravity-awesome"},
    {"slot": 60, "module_id": 4, "slug": "sql-injection-testing",         "source": "antigravity-awesome"},
    # Module 5
    {"slot": 61, "module_id": 5, "slug": "prompt-engineering-patterns",   "source": "wshobson-agents"},
    {"slot": 62, "module_id": 5, "slug": "rag-implementation",            "source": "wshobson-agents"},
    {"slot": 63, "module_id": 5, "slug": "langchain-architecture",        "source": "wshobson-agents"},
    {"slot": 64, "module_id": 5, "slug": "langgraph-fundamentals",        "source": "langchain-skills"},
    {"slot": 65, "module_id": 5, "slug": "langgraph-persistence",         "source": "langchain-skills"},
    {"slot": 66, "module_id": 5, "slug": "langgraph-human-in-the-loop",   "source": "langchain-skills"},
    {"slot": 67, "module_id": 5, "slug": "langchain-fundamentals",        "source": "langchain-skills"},
    {"slot": 68, "module_id": 5, "slug": "langchain-rag",                 "source": "langchain-skills"},
    {"slot": 69, "module_id": 5, "slug": "langchain-middleware",          "source": "langchain-skills"},
    {"slot": 70, "module_id": 5, "slug": "deep-agents-core",              "source": "langchain-skills"},
    {"slot": 71, "module_id": 5, "slug": "deep-agents-memory",            "source": "langchain-skills"},
    {"slot": 72, "module_id": 5, "slug": "autonomous-agent-patterns",     "source": "antigravity-awesome"},
    {"slot": 73, "module_id": 5, "slug": "agent-memory-systems",          "source": "antigravity-awesome"},
    {"slot": 74, "module_id": 5, "slug": "langfuse",                      "source": "antigravity-awesome"},
    {"slot": 75, "module_id": 5, "slug": "llm-evaluation",                "source": "wshobson-agents"},
    # Module 6
    {"slot": 76, "module_id": 6, "slug": "test-driven-development",       "source": "obra-superpowers"},
    {"slot": 77, "module_id": 6, "slug": "systematic-debugging",          "source": "obra-superpowers"},
    {"slot": 78, "module_id": 6, "slug": "verification-before-completion","source": "obra-superpowers"},
    {"slot": 79, "module_id": 6, "slug": "requesting-code-review",        "source": "obra-superpowers"},
    {"slot": 80, "module_id": 6, "slug": "webapp-testing",                "source": "anthropic-skills"},
    {"slot": 81, "module_id": 6, "slug": "web-testing-playwright-e2e",    "source": "agents-inc"},
    {"slot": 82, "module_id": 6, "slug": "web-testing-cypress-e2e",       "source": "agents-inc"},
    {"slot": 83, "module_id": 6, "slug": "e2e-testing",                   "source": "opencode-configs"},
    {"slot": 84, "module_id": 6, "slug": "observability-engineer",        "source": "antigravity-awesome"},
    {"slot": 85, "module_id": 6, "slug": "receiving-code-review",        "source": "antigravity-awesome"},
    # Module 7
    {"slot": 86,  "module_id": 7, "slug": "docker-build-strategies",      "source": "docker-skills"},
    {"slot": 87,  "module_id": 7, "slug": "docker-compose-patterns",      "source": "docker-skills"},
    {"slot": 88,  "module_id": 7, "slug": "terraform-skill",              "source": "terraform-skill"},
    {"slot": 89,  "module_id": 7, "slug": "kubernetes-deployment",        "source": "antigravity-awesome"},
    {"slot": 90,  "module_id": 7, "slug": "kubernetes-skill",             "source": "kubernetes-skill"},
    {"slot": 91,  "module_id": 7, "slug": "infra-ci-cd-github-actions",   "source": "agents-inc"},
    {"slot": 92,  "module_id": 7, "slug": "terraform-policy",             "source": "hashicorp"},
    {"slot": 93,  "module_id": 7, "slug": "aws-cdk-development",          "source": "antigravity-awesome"},
    {"slot": 94,  "module_id": 7, "slug": "cloud-devops",                 "source": "antigravity-awesome"},
    {"slot": 95,  "module_id": 7, "slug": "aws-serverless",               "source": "antigravity-awesome"},
    {"slot": 96,  "module_id": 7, "slug": "azure-devops",                 "source": "antigravity-awesome"},
    {"slot": 97,  "module_id": 7, "slug": "devops-deploy",                "source": "antigravity-awesome"},
    {"slot": 98,  "module_id": 7, "slug": "aws-serverless-eda",           "source": "antigravity-awesome"},
    {"slot": 99,  "module_id": 7, "slug": "application-performance-performance-optimization", "source": "antigravity-awesome"},
    {"slot": 100, "module_id": 7, "slug": "bash-linux",                   "source": "antigravity-awesome"},
]

# vendor-published sources get a scoring bonus
_VENDOR_SOURCES = {
    "anthropic-skills", "vercel-agent-skills", "nextjs-official",
    "supabase", "neon", "prisma", "firebase", "redis", "clickhouse",
    "hashicorp", "terraform-skill", "aws-skills", "kubernetes-skill",
    "docker-skills", "stripe", "cloudflare", "hono", "better-auth",
    "convex", "langchain-skills", "callstack-rn",
}

# ---------------------------------------------------------------------------
# Catalog I/O
# ---------------------------------------------------------------------------


def _catalog_path(config: dict) -> Path:
    root = config.get("_project_root", Path.cwd())
    return Path(root) / "DevCrew-Vault" / "catalog.yaml"


def load_catalog(config: dict) -> dict[str, Any]:
    """Load ``catalog.yaml``; return default structure if not found."""
    path = _catalog_path(config)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        # Merge in any missing modules from defaults
        existing_ids = {m["id"] for m in data.get("modules", [])}
        for mod in _DEFAULT_MODULES:
            if mod["id"] not in existing_ids:
                data.setdefault("modules", []).append(mod)
        for m in data.get("modules", []):
            if not m.get("alternates"):
                for dmod in _DEFAULT_MODULES:
                    if dmod["id"] == m.get("id"):
                        m["alternates"] = list(dmod.get("alternates", []))
                        break
        return data
    return _build_default_catalog()


def save_catalog(catalog: dict[str, Any], config: dict) -> None:
    """Write ``catalog.yaml`` atomically."""
    path = _catalog_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.dump(catalog, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp.replace(path)


def _build_default_catalog() -> dict[str, Any]:
    """Generate the default catalog structure from embedded data."""
    # Group pinned slots by module
    slots_by_module: dict[int, list[dict]] = {}
    for slot in _PINNED_SLOTS:
        mid = slot["module_id"]
        slots_by_module.setdefault(mid, []).append(slot)

    modules = []
    for mod in _DEFAULT_MODULES:
        mid = mod["id"]
        modules.append({
            "id": mid,
            "name": mod["name"],
            "target": mod["target"],
            "keywords": mod["keywords"],
            "pinned_slots": [
                {
                    "slot": s["slot"],
                    "slug": s["slug"],
                    "source": s["source"],
                    "status": "pending",  # filled in by select_skills
                }
                for s in sorted(slots_by_module.get(mid, []), key=lambda x: x["slot"])
            ],
            "alternates": list(mod.get("alternates", [])),
            "overrides": {},  # manual slug → module_id overrides
        })

    return {
        "version": 2,
        "modules": modules,
        "dedup_policy": "keep-vendor-first",
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_skill(
    slug: str,
    name: str,
    description: str,
    body: str,
    catalog: dict[str, Any],
    source_name: str = "",
) -> tuple[int, float]:
    """Score a skill against each module and return the best (module_id, score).

    Scoring:
    * +2 for each keyword hit in name
    * +1 for each keyword hit in description
    * +0.5 for each keyword hit in body (capped at 5)
    * +3 if source is vendor-published
    * Manual override in ``catalog.overrides`` wins unconditionally.

    Parameters
    ----------
    slug, name, description, body:
        Skill metadata.
    catalog:
        Loaded catalog dict.
    source_name:
        The source that provided this skill.

    Returns
    -------
    tuple[int, float]
        ``(module_id, score)``
    """
    # Check manual override first
    for mod in catalog.get("modules", []):
        overrides: dict = mod.get("overrides", {})
        if slug in overrides:
            return mod["id"], 999.0

    text_name = (name + " " + slug).lower()
    text_desc = description.lower()
    text_body = body.lower()

    best_id = 1
    best_score = -1.0

    for mod in catalog.get("modules", _DEFAULT_MODULES):
        score = 0.0
        keywords: list[str] = mod.get("keywords", [])
        body_hits = 0
        for kw in keywords:
            kw_low = kw.lower()
            if kw_low in text_name:
                score += 2.0
            if kw_low in text_desc:
                score += 1.0
            if body_hits < 10 and kw_low in text_body:
                score += 0.5
                body_hits += 1

        # Vendor bonus
        if source_name in _VENDOR_SOURCES:
            score += 3.0

        if score > best_score:
            best_score = score
            best_id = mod["id"]

    return best_id, best_score


# ---------------------------------------------------------------------------
# Selection + deduplication
# ---------------------------------------------------------------------------


def _slug_exists_in_vault(slug: str, conn: sqlite3.Connection) -> bool:
    """Check if a slug exists in the skills table."""
    cur = conn.execute("SELECT 1 FROM skills WHERE slug = ? LIMIT 1", (slug,))
    return cur.fetchone() is not None


def _candidate_rank_key(skill: dict, score: float) -> tuple[int, int, int, int, int, float]:
    val_status = skill.get("validation_status", "")
    val_rank = 2 if val_status == "valid" else (1 if val_status == "valid-with-warnings" else 0)

    lic = (skill.get("license") or "").upper()
    lic_rank = 1 if lic in ("MIT", "APACHE-2.0", "BSD-3-CLAUSE", "CC-BY-4.0", "MPL-2.0") else 0

    desc = (skill.get("description") or "").lower()
    trigger_words = ("use when", "trigger", "when to use", "activate", "use for", "recommended for")
    trigger_rank = 1 if any(tw in desc for tw in trigger_words) else 0

    extras_rank = 1 if (skill.get("has_scripts") or skill.get("has_references")) else 0

    src = skill.get("source_name") or ""
    vendor_rank = 1 if src in _VENDOR_SOURCES else 0

    return (val_rank, lic_rank, vendor_rank, trigger_rank, extras_rank, score)


def select_skills(
    config: dict,
    conn: sqlite3.Connection,
    catalog: dict[str, Any],
) -> None:
    """Classify and assign all ingested skills to modules.

    Algorithm:
    1. For each pinned slot, look for the exact slug (or namespaced variant)
       in the skills table. Mark it ``selected`` if found + valid + licensed.
       Mark ``unfilled`` in catalog if missing.
    2. Fill any ``unfilled`` slots from the module's ``alternates`` list.
    3. For every remaining skill, classify it and add it as a ``candidate``.
    4. Deduplicate: when two slugs are near-duplicates, keep the vendor or
       highest-scoring one as ``selected``; mark the other ``alternate``.
    5. Fill any remaining unfilled slots up to the module target from the
       ranked candidate pool.

    Parameters
    ----------
    config: Loaded config dict.
    conn:   Open SQLite connection.
    catalog: Loaded catalog dict.
    """
    all_skills = list_skills(conn)
    # Build a lookup: slug → skill row
    skill_map: dict[str, dict] = {s["slug"]: s for s in all_skills}

    allowed_licenses = set(config.get("allowed_licenses", []))
    disallowed_slugs = {
        "differential-review",
        "variant-analysis",
        "sharp-edges",
        "supply-chain-risk-auditor",
        "agentic-actions-auditor",
        "solidity-security",
        "redis-security",
        "spring-security",
        "dispatching-parallel-agents",
        "temporal-python-testing",
        "docker-development",
        "extension-to-functions-codebase",
    }

    def _is_allowed(sk: dict | None) -> bool:
        if not sk:
            return False
        if sk.get("validation_status") == "invalid":
            return False
        if sk.get("slug") in disallowed_slugs:
            return False
        lic = sk.get("license", "")
        if allowed_licenses and lic not in allowed_licenses:
            return False
        p_str = sk.get("path", "")
        if "_quarantine" in Path(p_str).parts:
            return False
        return True

    # Reset existing assignments to candidate before re-evaluating
    conn.execute("UPDATE skill_modules SET status = 'candidate', rank = 500.0")

    # Track which slugs have been assigned a module already
    assigned: dict[str, int] = {}  # slug → module_id

    # Pass 1: Pinned slots
    for slot in _PINNED_SLOTS:
        slug = slot["slug"]
        module_id = slot["module_id"]

        # Exact match or find a namespaced variant (e.g. source--slug)
        matched_slug = None
        if slug in skill_map:
            matched_slug = slug
        else:
            # Try namespaced variants
            for sk in skill_map:
                if sk.endswith(f"--{slug}") or sk == slug:
                    matched_slug = sk
                    break

        if matched_slug and _is_allowed(skill_map.get(matched_slug)):
            upsert_skill_module(conn, matched_slug, module_id, rank=float(slot["slot"]), score=100.0, status="selected")
            assigned[matched_slug] = module_id
            # Update catalog pinned slot status
            _update_pinned_status(catalog, slot["slot"], "selected", matched_slug)
        else:
            _update_pinned_status(catalog, slot["slot"], "unfilled", slug)

    # Pass 2: Alternates for unfilled slots
    for mod in catalog.get("modules", []):
        module_id = mod["id"]
        unfilled_count = sum(
            1 for s in mod.get("pinned_slots", []) if s.get("status") == "unfilled"
        )
        for alt_slug in mod.get("alternates", []):
            if unfilled_count <= 0:
                break
            matched_alt = None
            if alt_slug in skill_map:
                matched_alt = alt_slug
            else:
                for sk in skill_map:
                    if sk.endswith(f"--{alt_slug}"):
                        matched_alt = sk
                        break
            if matched_alt and matched_alt not in assigned and _is_allowed(skill_map.get(matched_alt)):
                upsert_skill_module(conn, matched_alt, module_id, rank=200.0, score=50.0, status="selected")
                assigned[matched_alt] = module_id
                unfilled_count -= 1

    # Pass 3: Classify all remaining skills as candidates
    for skill in all_skills:
        slug = skill["slug"]
        if slug in assigned:
            continue
        mod_id, score = classify_skill(
            slug=slug,
            name=skill.get("name", ""),
            description=skill.get("description", ""),
            body=skill.get("body", ""),
            catalog=catalog,
            source_name=skill.get("source_name", ""),
        )
        upsert_skill_module(conn, slug, mod_id, rank=500.0, score=score, status="candidate")
        assigned[slug] = mod_id

    # Pass 4: Deduplication — detect near-duplicates by name similarity
    _deduplicate(conn, catalog, skill_map)

    # Pass 5: Fill remaining unfilled slots up to module target from ranked candidate pool
    for mod in catalog.get("modules", []):
        mid = mod["id"]
        target = mod.get("target", 15)
        cur = conn.execute(
            "SELECT COUNT(*) FROM skill_modules WHERE module_id = ? AND status = 'selected'",
            (mid,),
        )
        current_selected = cur.fetchone()[0]
        needed = target - current_selected
        if needed > 0:
            cand_rows = conn.execute(
                "SELECT slug, score FROM skill_modules WHERE module_id = ? AND status = 'candidate'",
                (mid,),
            ).fetchall()
            scored_cands = []
            for c_slug, c_score in cand_rows:
                sk = skill_map.get(c_slug)
                if not _is_allowed(sk):
                    continue
                rank_key = _candidate_rank_key(sk, c_score)
                scored_cands.append((rank_key, c_slug, c_score))
            scored_cands.sort(key=lambda x: x[0], reverse=True)
            for idx, (_, c_slug, c_score) in enumerate(scored_cands[:needed]):
                upsert_skill_module(
                    conn, c_slug, mid, rank=300.0 + idx, score=c_score, status="selected"
                )

    save_catalog(catalog, config)


def _update_pinned_status(catalog: dict, slot_num: int, status: str, slug: str) -> None:
    """Update the status field of a pinned slot in the catalog."""
    for mod in catalog.get("modules", []):
        for ps in mod.get("pinned_slots", []):
            if ps["slot"] == slot_num:
                ps["status"] = status
                ps["matched_slug"] = slug
                return


def _deduplicate(
    conn: sqlite3.Connection,
    catalog: dict[str, Any],
    skill_map: dict[str, dict],
) -> None:
    """Detect and mark near-duplicate skills.

    Two skills are near-duplicates if:
    - Their names are identical (after slugify normalisation), OR
    - Their descriptions share > 80% of tokens.

    The duplicate with the lower score (or non-vendor source) is marked
    ``alternate``.
    """
    seen_names: dict[str, str] = {}  # normalised_name → slug

    rows = list_skill_modules(conn)
    # Sort: selected first (so selected beats candidate in dedup)
    rows.sort(key=lambda r: ({"selected": 0, "candidate": 1, "alternate": 2}.get(r.get("status", "candidate"), 1)))

    for row in rows:
        slug = row["slug"]
        name = (row.get("name") or slug).lower().replace("-", " ").strip()
        if name in seen_names:
            other_slug = seen_names[name]
            # Keep the first one as selected/candidate; mark this one alternate
            conn.execute(
                "UPDATE skill_modules SET status = 'alternate' WHERE slug = ? AND status = 'candidate'",
                (slug,),
            )
            conn.commit()
        else:
            seen_names[name] = slug


# ---------------------------------------------------------------------------
# skill_modules reconciliation (called by watcher on add/change/delete)
# ---------------------------------------------------------------------------


def sync_skill_modules(
    slug: str,
    skill: dict[str, Any],
    conn: sqlite3.Connection,
    catalog: dict[str, Any],
    deleted: bool = False,
) -> None:
    """Update ``skill_modules`` for a single skill after a vault event.

    Parameters
    ----------
    slug:    Skill slug.
    skill:   Skill row dict (from ``list_skills`` / ``get_skill``).
    conn:    Open SQLite connection.
    catalog: Loaded catalog dict.
    deleted: If *True*, remove the row from ``skill_modules``.
    """
    if deleted:
        delete_skill_module(conn, slug)
        return

    # Check if this slug is a pinned slot
    for ps in _PINNED_SLOTS:
        if ps["slug"] == slug or slug.endswith(f"--{ps['slug']}"):
            if skill.get("validation_status") != "invalid":
                upsert_skill_module(
                    conn, slug, ps["module_id"], rank=ps["slot"], score=100.0, status="selected"
                )
                return

    # Otherwise classify
    mod_id, score = classify_skill(
        slug=slug,
        name=skill.get("name", ""),
        description=skill.get("description", ""),
        body=skill.get("body", ""),
        catalog=catalog,
        source_name=skill.get("source_name", ""),
    )
    upsert_skill_module(conn, slug, mod_id, rank=500.0, score=score, status="candidate")


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


def generate_coverage_report(config: dict) -> Path:
    """Generate ``coverage-report.md`` and return its path.

    Parameters
    ----------
    config: Loaded config dict.

    Returns
    -------
    Path
        Path to the written coverage report.
    """
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    init_db(conn)
    catalog = load_catalog(config)
    select_skills(config, conn, catalog)

    counts = module_counts(conn)

    lines = [
        "# DevCrew Vault — Coverage Report\n\n",
        f"Generated: `{__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`\n\n",
        "| Module | Selected | Target | Shortfall | Candidates | Alternates |\n",
        "|--------|----------|--------|-----------|------------|------------|\n",
    ]

    all_shortfall = 0
    for mod in catalog.get("modules", _DEFAULT_MODULES):
        mid = mod["id"]
        target = mod["target"]
        mc = counts.get(mid, {})
        selected = mc.get("selected", 0)
        candidates = mc.get("candidate", 0)
        alternates = mc.get("alternate", 0)
        shortfall = max(0, target - selected)
        all_shortfall += shortfall
        indicator = "✅" if shortfall == 0 else "❌"
        lines.append(
            f"| {mid}. {mod['name']} | {selected} | {target} | "
            f"{indicator} {shortfall} | {candidates} | {alternates} |\n"
        )

    lines.append(f"\n**Total shortfall:** {all_shortfall} skill(s)\n\n")

    # Per-module skill lists
    for mod in catalog.get("modules", _DEFAULT_MODULES):
        mid = mod["id"]
        lines.append(f"\n## Module {mid}: {mod['name']}\n\n")
        module_rows = list_skill_modules(conn, module_id=mid)

        selected_rows = [r for r in module_rows if r.get("status") == "selected"]
        alt_rows = [r for r in module_rows if r.get("status") == "alternate"]

        if selected_rows:
            lines.append("### Selected\n\n")
            for r in selected_rows:
                lines.append(f"- `{r['slug']}` — {(r.get('description') or '')[:80]}\n")

        if alt_rows:
            lines.append("\n### Alternates\n\n")
            for r in alt_rows:
                lines.append(f"- `{r['slug']}` _(alternate)_\n")

        # Pinned unfilled
        unfilled = [
            ps for ps in mod.get("pinned_slots", [])
            if ps.get("status") == "unfilled"
        ]
        if unfilled:
            lines.append("\n### ⚠️ Unfilled Pinned Slots\n\n")
            for ps in unfilled:
                lines.append(f"- Slot {ps['slot']}: `{ps['slug']}` (from `{ps.get('source', '?')}`)\n")

    conn.close()

    root = config.get("_project_root", Path.cwd())
    report_path = Path(root) / "coverage-report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# CLI helper (used by watcher.py module commands)
# ---------------------------------------------------------------------------


def cmd_modules(config: dict) -> None:
    """Print per-module skill counts."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    init_db(conn)
    catalog = load_catalog(config)
    counts = module_counts(conn)
    conn.close()

    print(f"\n{'=' * 70}")
    print(f"{'Module':<45} {'Sel':>4} {'Tgt':>4} {'Cand':>5} {'Alt':>4}")
    print(f"{'=' * 70}")
    for mod in catalog.get("modules", _DEFAULT_MODULES):
        mid = mod["id"]
        target = mod["target"]
        mc = counts.get(mid, {})
        sel = mc.get("selected", 0)
        cand = mc.get("candidate", 0)
        alt = mc.get("alternate", 0)
        indicator = "✅" if sel >= target else f"❌ -{target - sel}"
        name = f"{mid}. {mod['name']}"
        print(f"{name:<45} {sel:>4} {target:>4} {cand:>5} {alt:>4}  {indicator}")
    print()


def cmd_module(config: dict, module_id: int) -> None:
    """Print skills in a specific module."""
    vault_cfg = config.get("vault", {})
    db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    conn = get_connection(db_path)
    init_db(conn)
    catalog = load_catalog(config)
    rows = list_skill_modules(conn, module_id=module_id)
    conn.close()

    mod_name = next(
        (m["name"] for m in catalog.get("modules", _DEFAULT_MODULES) if m["id"] == module_id),
        f"Module {module_id}",
    )
    print(f"\n{'=' * 70}")
    print(f"Module {module_id}: {mod_name}")
    print(f"{'=' * 70}")
    for row in rows:
        icon = {"selected": "✅", "candidate": "⬜", "alternate": "🔁"}.get(row.get("status", ""), "?")
        print(
            f"  {icon} [{row.get('status', '?'):10s}] {row['slug']:<40} "
            f"score={row.get('score', 0):.1f}"
        )
    print()

