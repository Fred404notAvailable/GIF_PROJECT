"""
update_catalog_slots.py — Update catalog.yaml with strict pinned slot matching and separate unpinned backfills.
"""

import yaml
import sqlite3
from pathlib import Path

def update_catalog():
    cat_path = Path("DevCrew-Vault/catalog.yaml")
    with open(cat_path, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    conn = sqlite3.connect("DevCrew-Vault/registry.db")
    cur = conn.cursor()

    # Selected skills in DB
    cur.execute("""
        SELECT sm.slug, s.source_name, s.license, sm.module_id, s.name
        FROM skill_modules sm
        JOIN skills s ON sm.slug = s.slug
        WHERE sm.status = 'selected'
    """)
    selected_by_slug = {r[0]: {"source": r[1], "license": r[2], "module_id": r[3], "name": r[4]} for r in cur.fetchall()}

    # Strict pinned slot definitions (1-100) with their canonical target
    # Double assignments removed
    PINNED_DEFINITIONS = {
        # Mod 1: 15 slots
        1: ("api-design-principles", "wshobson-agents", 1),
        2: ("architecture-patterns", "wshobson-agents", 1),
        3: ("microservices-patterns", "wshobson-agents", 1),
        4: ("dotnet-backend-patterns", "wshobson-agents", 1),
        5: ("nodejs-backend-patterns", "wshobson-agents", 1),
        6: ("fastapi-templates", "wshobson-agents", 1),
        7: ("workflow-orchestration-patterns", "wshobson-agents", 1),
        8: ("event-store-design", "wshobson-agents", 1),
        9: ("hono", "hono", 1),
        10: ("cloudflare", "cloudflare", 1),
        11: ("better-auth-best-practices", "better-auth", 1),
        12: ("better-auth-security-best-practices", "better-auth", 1),
        13: ("stripe-best-practices", "stripe", 1),
        14: ("mcp-builder", "anthropic-skills", 1),
        15: ("backend-development", "claudekit", 1),

        # Mod 2: 15 slots
        16: ("frontend-design", "anthropic-skills", 2),
        17: ("web-artifacts-builder", "anthropic-skills", 2),
        18: ("react-best-practices", "vercel-agent-skills", 2),
        19: ("next-dev-loop", "nextjs-official", 2),
        20: ("tailwind-design-system", "wshobson-agents", 2),
        21: ("react-native-best-practices", "callstack-rn", 2),
        22: ("frontend-patterns", "everything-claude-code", 2),
        23: ("web-ui-shadcn-ui", "agents-inc", 2),
        24: ("angular-best-practices", "antigravity-awesome", 2),
        25: ("server-actions", "szum-tech", 2),
        26: ("react-19-compiler", "szum-tech", 2),
        27: ("tailwind-css-4", "szum-tech", 2),
        28: ("storybook-testing", "szum-tech", 2),
        29: ("svelte", "modernstack", 2),
        30: ("ui-visual-validator", "antigravity-awesome", 2),

        # Mod 3: 15 slots
        31: ("supabase-postgres-best-practices", "supabase", 3),
        32: ("supabase", "supabase", 3),
        33: ("neon-postgres", "neon", 3),
        34: ("neon-postgres-branches", "neon", 3),
        35: ("prisma-postgres-setup", "prisma", 3),
        36: ("prisma-cli", "prisma", 3),
        37: ("firebase-basics", "firebase", 3),
        38: ("sql-optimization-patterns", "wshobson-agents", 3),
        39: ("database-migration", "wshobson-agents", 3),
        40: ("postgresql-table-design", "wshobson-agents", 3),
        41: ("clickhouse-best-practices", "clickhouse", 3),
        42: ("vector-index-tuning", "wshobson-agents", 3),
        43: ("similarity-search-patterns", "wshobson-agents", 3),
        44: ("hybrid-search-implementation", "wshobson-agents", 3),
        45: ("embedding-strategies", "wshobson-agents", 3),

        # Mod 4: 15 slots
        46: ("secauditor", "secauditor", 4),
        47: ("security-audit", "antigravity-awesome", 4),
        48: ("secure-webapp", "secure-webapp", 4),
        49: ("owasp-audit", "cybersecurity-skills", 4),
        50: ("insecure-defaults", "trailofbits", 4),
        51: ("differential-review", "trailofbits", 4),
        52: ("semgrep", "trailofbits", 4),
        53: ("codeql", "trailofbits", 4),
        54: ("sarif-parsing", "trailofbits", 4),
        55: ("variant-analysis", "trailofbits", 4),
        56: ("sharp-edges", "trailofbits", 4),
        57: ("supply-chain-risk-auditor", "trailofbits", 4),
        58: ("agentic-actions-auditor", "trailofbits", 4),
        59: ("firebase-security-rules-auditor", "firebase", 4),
        60: ("stride-analysis-patterns", "wshobson-agents", 4),

        # Mod 5: 15 slots
        61: ("prompt-engineering-patterns", "wshobson-agents", 5),
        62: ("rag-implementation", "wshobson-agents", 5),
        63: ("langchain-architecture", "wshobson-agents", 5),
        64: ("langgraph-fundamentals", "langchain-skills", 5),
        65: ("langgraph-persistence", "langchain-skills", 5),
        66: ("langgraph-human-in-the-loop", "langchain-skills", 5),
        67: ("langchain-fundamentals", "langchain-skills", 5),
        68: ("langchain-rag", "langchain-skills", 5),
        69: ("langchain-middleware", "langchain-skills", 5),
        70: ("deep-agents-core", "langchain-skills", 5),
        71: ("deep-agents-memory", "langchain-skills", 5),
        72: ("autonomous-agent-patterns", "antigravity-awesome", 5),
        73: ("agent-memory-systems", "antigravity-awesome", 5),
        74: ("langfuse", "antigravity-awesome", 5),
        75: ("llm-evaluation", "wshobson-agents", 5),

        # Mod 6: 10 slots
        76: ("test-driven-development", "obra-superpowers", 6),
        77: ("systematic-debugging", "obra-superpowers", 6),
        78: ("verification-before-completion", "obra-superpowers", 6),
        79: ("requesting-code-review", "obra-superpowers", 6),
        80: ("webapp-testing", "anthropic-skills", 6),
        81: ("web-testing", "claudekit", 6),
        82: ("testing-perf", "orchestkit", 6),
        83: ("e2e-testing", "opencode-configs", 6),
        84: ("testing-best-practices", "opencode-configs", 6),
        85: ("observability-engineer", "antigravity-awesome", 6),

        # Mod 7: 15 slots
        86: ("docker", "docker-skills", 7),
        87: ("docker-development", "docker-development", 7),
        88: ("dockerfile-best-practices", "opencode-configs", 7),
        89: ("kubernetes-manifests", "opencode-configs", 7),
        90: ("kubernetes-skill", "kubernetes-skill", 7),
        91: ("terraform-skill", "terraform-skill", 7),
        92: ("terraform", "hashicorp", 7),
        93: ("aws", "aws-skills", 7),
        94: ("devops-deployment", "orchestkit", 7),
        95: ("ansible", "blastum-skills", 7),
        96: ("github-cli", "blastum-skills", 7),
        97: ("q24-github-actions-generator", "q24-devops", 7),
        98: ("q24-helm-generator", "q24-devops", 7),
        99: ("application-performance-performance-optimization", "antigravity-awesome", 7),
        100: ("bash-linux", "antigravity-awesome", 7),
    }

    UNFILLED_REASONS = {
        11: "upstream repository has no LICENSE file; license unknown",
        12: "upstream repository has no LICENSE file; license unknown",
        15: "upstream repository has no LICENSE file; license unknown",
        28: "skill located only in internal test fixture, not distributed",
        29: "upstream repository has no LICENSE file; license unknown",
        46: "repository not cloned / inaccessible",
        50: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        51: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        52: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        53: "Trail of Bits codeql is CC-BY-SA-4.0; MIT codeql selected in Module 4",
        54: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        55: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        56: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        57: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        58: "license CC-BY-SA-4.0 requires user decision (ShareAlike not in allowed_licenses)",
        81: "skill not found in repo; claudekit uses web-testing-playwright-e2e",
        82: "skill not found in orchestkit",
        84: "skill not found in opencode-configs",
        86: "docker-skills provides docker-build-strategies, not bare docker",
        87: "skill not found in docker-development repo",
        88: "skill not found in opencode-configs",
        89: "skill not found in opencode-configs",
        92: "HashiCorp MPL-2.0 license omitted from allowed_licenses",
        93: "aws-skills provides aws-cdk-development, not bare aws",
        94: "skill not found in orchestkit",
        95: "skill not found in blastum-skills",
        96: "skill not found in blastum-skills",
        97: "skill not found in q24-devops",
        98: "skill not found in q24-devops",
    }

    used_skills = set()
    mod_pinned_slots = {i: [] for i in range(1, 8)}

    for slot in range(1, 101):
        slug, src, mod_id = PINNED_DEFINITIONS[slot]
        if slug in selected_by_slug and slug not in used_skills:
            used_skills.add(slug)
            mod_pinned_slots[mod_id].append({
                "slot": slot,
                "slug": slug,
                "matched_slug": slug,
                "source": selected_by_slug[slug]["source"],
                "status": "matched",
            })
        else:
            reason = UNFILLED_REASONS.get(slot, "skill not found in upstream source")
            mod_pinned_slots[mod_id].append({
                "slot": slot,
                "slug": slug,
                "matched_slug": None,
                "source": src,
                "status": f"unfilled ({reason})",
            })

    # Find unpinned backfills
    backfills_by_mod = {i: [] for i in range(1, 8)}
    for slug, info in selected_by_slug.items():
        if slug not in used_skills:
            mid = info["module_id"]
            backfills_by_mod[mid].append({
                "slug": slug,
                "name": info["name"],
                "source": info["source"],
                "license": info["license"],
                "reason": "Top-ranked validated curriculum candidate",
            })

    # Update modules in catalog
    for mod in catalog.get("modules", []):
        mid = mod["id"]
        mod["pinned_slots"] = mod_pinned_slots[mid]
        mod["backfill_skills"] = backfills_by_mod[mid]

    with open(cat_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(catalog, f, sort_keys=False)

    print(f"Updated {cat_path} with strict pinned slots and separate backfills.")
    conn.close()

if __name__ == "__main__":
    update_catalog()

