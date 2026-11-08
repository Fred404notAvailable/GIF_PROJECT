"""
repoint_skills.py — Execute Source Preference Re-pointing & License Reconciliation.
==================================================================================
1. Re-points 31 selected skills from aggregator mirrors to verified upstream sources.
2. Namespaces old aggregator copies to 'antigravity-awesome--<slug>' and keeps as alternate.
3. Marks remaining aggregator skills with provenance: aggregator-mirror in .source.json.
4. Namespaces un-namespaced duplicate directories in _quarantine to fix verify_vault.py.
5. Reconciles MPL-2.0 slot 92 to unfilled pending user decision in DECISIONS-NEEDED.md.
6. Updates registry.db (skills, skill_modules) and records content SHA diffs.
"""

import json
import shutil
import sqlite3
import yaml
from pathlib import Path
from datetime import datetime, timezone

from sync_skills import atomic_copy_skill, detect_license, write_source_json, read_source_json
from parsing import parse_skill_md, content_sha256
from git_ops import git_available, get_commit_sha

AGGREGATORS = {"antigravity-awesome", "awesome-copilot", "everything-claude-code"}

REPOINT_TARGETS = [
    ("api-design-principles", "wshobson-agents", Path(".staging/wshobson-agents/plugins/backend-development/skills/api-design-principles")),
    ("architecture-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/backend-development/skills/architecture-patterns")),
    ("microservices-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/backend-development/skills/microservices-patterns")),
    ("dotnet-backend-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/dotnet-contribution/skills/dotnet-backend-patterns")),
    ("nodejs-backend-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/javascript-typescript/skills/nodejs-backend-patterns")),
    ("fastapi-templates", "wshobson-agents", Path(".staging/wshobson-agents/plugins/api-scaffolding/skills/fastapi-templates")),
    ("workflow-orchestration-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/backend-development/skills/workflow-orchestration-patterns")),
    ("event-store-design", "wshobson-agents", Path(".staging/wshobson-agents/plugins/backend-development/skills/event-store-design")),
    ("convex", "convex", Path(".staging/convex/skills/convex")),
    ("tailwind-design-system", "wshobson-agents", Path(".staging/wshobson-agents/plugins/frontend-mobile-development/skills/tailwind-design-system")),
    ("supabase-postgres-best-practices", "supabase", Path(".staging/supabase/skills/supabase-postgres-best-practices")),
    ("supabase", "supabase", Path(".staging/supabase/skills/supabase")),
    ("neon-postgres", "neon", Path(".staging/neon/plugins/neon-postgres/skills/neon-postgres")),
    ("sql-optimization-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/developer-essentials/skills/sql-optimization-patterns")),
    ("database-migration", "wshobson-agents", Path(".staging/wshobson-agents/plugins/framework-migration/skills/database-migration")),
    ("vector-index-tuning", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/vector-index-tuning")),
    ("similarity-search-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/similarity-search-patterns")),
    ("hybrid-search-implementation", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/hybrid-search-implementation")),
    ("embedding-strategies", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/embedding-strategies")),
    ("stride-analysis-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/security-scanning/skills/stride-analysis-patterns")),
    ("prompt-engineering-patterns", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/prompt-engineering-patterns")),
    ("rag-implementation", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/rag-implementation")),
    ("langchain-architecture", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/langchain-architecture")),
    ("llm-evaluation", "wshobson-agents", Path(".staging/wshobson-agents/plugins/llm-application-dev/skills/llm-evaluation")),
    ("test-driven-development", "obra-superpowers", Path(".staging/obra-superpowers/skills/test-driven-development")),
    ("systematic-debugging", "obra-superpowers", Path(".staging/obra-superpowers/skills/systematic-debugging")),
    ("verification-before-completion", "obra-superpowers", Path(".staging/obra-superpowers/skills/verification-before-completion")),
    ("requesting-code-review", "obra-superpowers", Path(".staging/obra-superpowers/skills/requesting-code-review")),
    ("receiving-code-review", "obra-superpowers", Path(".staging/obra-superpowers/skills/receiving-code-review")),
    ("aws-cdk-development", "aws-skills", Path(".staging/aws-skills/plugins/aws-iac/skills/aws-cdk-development")),
    ("aws-serverless-eda", "aws-skills", Path(".staging/aws-skills/plugins/serverless-eda/skills/aws-serverless-eda")),
]

UPSTREAM_ORIGIN_MAP = {
    "hono": "Hono Documentation (yusukebe/hono-skill)",
    "nodejs-best-practices": "Goldbergyoni Node.js Best Practices",
    "database-design": "Database Design & SQL Modeling Guide",
    "react-best-practices": "Vercel Published Performance Guidance (vercel-labs/agent-skills)",
    "frontend-patterns": "Everything Claude Code (affaan-m/everything-claude-code)",
    "angular-best-practices": "Angular Official Best Practices & Style Guide",
    "ui-visual-validator": "Antigravity Awesome Skills UI Patterns",
    "neon-postgres-branches": "Neon Database Branching Architecture Guidance",
    "security-audit": "Netresearch Security Audit Skill (netresearch/security-audit-skill)",
    "codeql": "Trail of Bits Static Analysis / CodeQL Guidance",
    "semgrep-rule-creator": "Trail of Bits Semgrep Rules",
    "api-security": "Trail of Bits API Security Audit",
    "api-security-testing": "Trail of Bits SARIF & Static Security Testing",
    "security-auditor": "Trail of Bits Variant Analysis",
    "security-review": "Trail of Bits Sharp Edges Review",
    "vulnerability-scanner": "Trail of Bits Supply Chain Risk Auditor",
    "web-security-testing": "Trail of Bits Agentic Actions Auditor",
    "xss-html-injection": "Firebase Security Rules & Web App Security",
    "sql-injection-testing": "OWASP SQL Injection Testing Guide",
    "autonomous-agent-patterns": "Anthropic Autonomous Agent Architecture Patterns",
    "agent-memory-systems": "Context Engineering / Agent Memory Patterns",
    "langfuse": "Langfuse Observability & Tracing Documentation",
    "e2e-testing": "OpenCode Configs E2E Testing Templates",
    "observability-engineer": "OpenCode Configs Observability & Testing Best Practices",
    "kubernetes-deployment": "OpenCode Configs Kubernetes Manifests",
    "cloud-devops": "Orchestkit DevOps Deployment Patterns",
    "aws-serverless": "Blastum AgentSkills Ansible / Serverless",
    "azure-devops": "Blastum AgentSkills GitHub CLI / Azure DevOps",
    "devops-deploy": "Q24 DevOps GitHub Actions Generator (remcovergoossen/q24devops)",
    "application-performance-performance-optimization": "Antigravity Awesome Skills Performance Patterns",
    "bash-linux": "Antigravity Awesome Skills Defensive Bash Patterns",
}

def main():
    repo_root = Path(".").resolve()
    vault_skills_dir = repo_root / "DevCrew-Vault" / "skills"
    quarantine_dir = repo_root / "DevCrew-Vault" / "_quarantine"
    db_path = repo_root / "DevCrew-Vault" / "registry.db"
    catalog_path = repo_root / "DevCrew-Vault" / "catalog.yaml"

    with open(repo_root / "devcrew.config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    source_cfg_map = {s["name"]: s for s in config.get("sources", [])}

    print("=== Step 1: Re-pointing 31 selected skills to upstream repositories ===")
    repoint_log = []

    for slug, upstream_source, upstream_dir in REPOINT_TARGETS:
        vault_dest = vault_skills_dir / slug
        src_cfg = source_cfg_map.get(upstream_source, {})
        repo_url = src_cfg.get("url", "")
        staging_repo = Path(".staging") / upstream_source
        commit_sha = get_commit_sha(staging_repo) if staging_repo.is_dir() and git_available() else "UNKNOWN"
        rel_upstream_path = str(upstream_dir.relative_to(staging_repo))
        license_id = detect_license(upstream_dir, staging_repo)

        old_source = "antigravity-awesome"
        old_meta = read_source_json(vault_dest) if vault_dest.exists() else None
        old_sha = old_meta.get("content_sha256", "") if old_meta else ""

        # 1. Namespace old aggregator copy to antigravity-awesome--<slug>
        agg_dest = vault_skills_dir / f"{old_source}--{slug}"
        if vault_dest.exists() and not agg_dest.exists():
            atomic_copy_skill(vault_dest, agg_dest)
            # update .source.json for the alternate
            write_source_json(
                agg_dest,
                source_name=old_source,
                repo_url=old_meta.get("repo_url", "") if old_meta else "",
                ref=old_meta.get("ref", "main") if old_meta else "main",
                commit_sha=old_meta.get("commit_sha", "") if old_meta else "",
                upstream_path=old_meta.get("upstream_path", "") if old_meta else "",
                license_id=old_meta.get("license", "MIT") if old_meta else "MIT",
                sha256=old_sha,
            )
            # Add provenance marker
            agg_source_json = agg_dest / ".source.json"
            if agg_source_json.exists():
                data = json.loads(agg_source_json.read_text(encoding="utf-8"))
                data["provenance"] = "aggregator-mirror"
                agg_source_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # 2. Copy upstream skill into vault_dest
        atomic_copy_skill(upstream_dir, vault_dest)
        new_sha = content_sha256(vault_dest)
        write_source_json(
            vault_dest,
            source_name=upstream_source,
            repo_url=repo_url,
            ref="main",
            commit_sha=commit_sha,
            upstream_path=rel_upstream_path,
            license_id=license_id,
            sha256=new_sha,
        )

        frontmatter, body = parse_skill_md(vault_dest / "SKILL.md")
        skill_name = frontmatter.get("name", slug)
        skill_desc = frontmatter.get("description", "")
        meta_dict = {k: v for k, v in frontmatter.items() if k not in ("name", "description")}

        # 3. Update DB: skills table for canonical slug
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE skills
            SET name = ?, description = ?, body = ?, frontmatter_json = ?, license = ?,
                source_name = ?, commit_sha = ?, path = ?, content_sha256 = ?,
                validation_status = 'valid', validation_messages = '[]',
                updated_at = ?
            WHERE slug = ?
        """, (
            skill_name,
            skill_desc,
            body,
            json.dumps(frontmatter, default=str),
            license_id,
            upstream_source,
            commit_sha,
            str(vault_dest.resolve()),
            new_sha,
            now_iso,
            slug,
        ))

        # Insert alternate into skills and skill_modules as alternate
        cur.execute("SELECT id FROM skills WHERE slug = ?", (f"{old_source}--{slug}",))
        existing_alt = cur.fetchone()
        if not existing_alt and agg_dest.exists():
            alt_frontmatter, alt_body = parse_skill_md(agg_dest / "SKILL.md")
            alt_name = alt_frontmatter.get("name", f"{old_source}--{slug}")
            alt_desc = alt_frontmatter.get("description", "")
            cur.execute("""
                INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status, validation_messages, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'valid', '[]', ?, ?)
            """, (
                f"{old_source}--{slug}",
                alt_name,
                alt_desc,
                alt_body,
                json.dumps(alt_frontmatter, default=str),
                "MIT",
                old_source,
                commit_sha,
                str(agg_dest.resolve()),
                old_sha,
                now_iso,
                now_iso,
            ))
            # insert into skill_modules as alternate
            cur.execute("SELECT module_id FROM skill_modules WHERE slug = ?", (slug,))
            mid_row = cur.fetchone()
            if mid_row:
                cur.execute("""
                    INSERT OR REPLACE INTO skill_modules (slug, module_id, rank, score, status)
                    VALUES (?, ?, 99, 50.0, 'alternate')
                """, (f"{old_source}--{slug}", mid_row[0]))

        repoint_log.append((slug, old_source, upstream_source, old_sha[:8], new_sha[:8], license_id))
        print(f"  [REPOINT] {slug}: {old_source} ({old_sha[:8]}) -> {upstream_source} ({new_sha[:8]}), license={license_id}")

    print(f"\n=== Step 2: Marking remaining 31 aggregator skills with provenance: aggregator-mirror ===")
    for slug, origin in UPSTREAM_ORIGIN_MAP.items():
        vdir = vault_skills_dir / slug
        s_file = vdir / ".source.json"
        if s_file.exists():
            data = json.loads(s_file.read_text(encoding="utf-8"))
            data["provenance"] = "aggregator-mirror"
            data["upstream_origin"] = origin
            s_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  [MIRROR] {slug}: marked aggregator-mirror, origin: {origin}")

    print("\n=== Step 3: Fixing quarantine directory duplicate slugs ===")
    # Any bare slug in _quarantine that duplicates a skills/ slug must be prefixed with its source
    quarantine_renames = [
        ("architecture-patterns", "orchestkit--architecture-patterns"),
        ("react-best-practices", "vercel-agent-skills--react-best-practices"),
        ("security-audit", "netresearch--security-audit"),
        ("codeql", "trailofbits--codeql"),
        ("semgrep-rule-creator", "trailofbits--semgrep-rule-creator"),
        ("systematic-debugging", "claudekit--systematic-debugging"),
        ("verification-before-completion", "claudekit--verification-before-completion"),
    ]
    for old_q_name, new_q_name in quarantine_renames:
        old_q = quarantine_dir / old_q_name
        new_q = quarantine_dir / new_q_name
        if old_q.is_dir():
            if new_q.exists():
                shutil.rmtree(new_q)
            old_q.rename(new_q)
            print(f"  [QUARANTINE-RENAME] {old_q_name} -> {new_q_name}")

    print("\n=== Step 4: Reconciling MPL-2.0 Slot 92 (terraform-policy) ===")
    # Slot 92 was terraform-policy from hashicorp (MPL-2.0). Revert to unfilled per Problem 2
    cur.execute("UPDATE skill_modules SET status = 'unfilled' WHERE slug = 'terraform-policy'")
    # Update catalog.yaml
    for m in catalog.get("modules", []):
        for ps in m.get("pinned_slots", []):
            if ps.get("slot") == 92:
                ps["status"] = "unfilled"
                ps["matched_slug"] = None
                ps["notes"] = "Unfilled: HashiCorp terraform-policy is MPL-2.0, which is omitted from allowed_licenses pending user approval in DECISIONS-NEEDED.md."
                print(f"  [CATALOG-RECONCILE] Slot 92 status set to unfilled (MPL-2.0 policy)")
    with open(catalog_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(catalog, f, sort_keys=False, allow_unicode=True)

    # Revert hashicorp-terraform-mcp-server-mcp to candidate
    cur.execute("UPDATE mcp_servers SET status = 'candidate', vetting_notes = vetting_notes || '; MPL-2.0 license omitted from allowed_licenses pending user approval' WHERE slug = 'hashicorp-terraform-mcp-server-mcp'")
    print("  [MCP-RECONCILE] hashicorp-terraform-mcp-server-mcp set to candidate (MPL-2.0)")

    conn.commit()
    conn.close()
    print("\nRepointing and reconciliation complete!")

if __name__ == "__main__":
    main()
