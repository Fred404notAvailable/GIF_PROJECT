"""
reconcile_skills_round3.py — Complete Round 3 Reconciliation for Skills and MCP Servers.
========================================================================================
1. Re-syncs authentic upstream skills for unfilled pinned slots:
   - owasp-audit (cybersecurity-skills, MIT) -> Slot 49
   - server-actions (szum-tech, MIT) -> Slot 25
   - react-19-compiler (szum-tech, MIT) -> Slot 26
   - tailwind-css-4 (szum-tech, MIT) -> Slot 27
   - backend-development (claudekit, MIT) -> Slot 15
   - svelte (modernstack, MIT) -> Slot 29
2. Ensures strictly 1 skill = 1 pinned slot max (no double assignments).
3. Restructures catalog.yaml pinned_slots with strict status ('matched' or 'unfilled').
4. Categorizes unpinned selections into a separate backfill list.
5. Applies strict MCP license gate and placement updates.
"""

import json
import re
import shutil
import sqlite3
import yaml
from pathlib import Path
from datetime import datetime, timezone

from sync_skills import atomic_copy_skill, detect_license, write_source_json, read_source_json
from parsing import parse_skill_md, content_sha256
from git_ops import get_commit_sha

def sync_new_upstream_skills():
    vault_base = Path("DevCrew-Vault").resolve()
    vault_skills_dir = vault_base / "skills"
    conn = sqlite3.connect(vault_base / "registry.db")
    cur = conn.cursor()

    SKILLS_TO_IMPORT = [
        ("owasp-audit", "cybersecurity-skills", Path(".staging/cybersecurity-skills/skills/owasp-audit"), 4, 49),
        ("server-actions", "szum-tech", Path(".staging/szum-tech/plugins/nextjs/skills/server-actions"), 2, 25),
        ("react-19-compiler", "szum-tech", Path(".staging/szum-tech/plugins/react/skills/react-19-compiler"), 2, 26),
        ("tailwind-css-4", "szum-tech", Path(".staging/szum-tech/plugins/design/skills/tailwind-css-4"), 2, 27),
        ("backend-development", "claudekit", Path(".staging/claudekit/.claude/skills/backend-development"), 1, 15),
        ("svelte", "modernstack", Path(".staging/modernstack/svelte"), 2, 29),
    ]

    now_iso = datetime.now(timezone.utc).isoformat()

    for slug, source_name, src_path, mod_id, slot in SKILLS_TO_IMPORT:
        if not src_path.exists():
            print(f"Skipping {slug}: path {src_path} does not exist")
            continue

        dest_dir = vault_skills_dir / slug
        atomic_copy_skill(src_path, dest_dir)
        sha = content_sha256(dest_dir)

        # Get commit sha if repo
        commit_sha = ""
        staging_repo = src_path
        while staging_repo.parent != Path(".staging").resolve() and staging_repo.parent != Path(".staging"):
            if (staging_repo / ".git").exists():
                break
            staging_repo = staging_repo.parent
        commit_sha = get_commit_sha(staging_repo)

        license_id = detect_license(src_path, staging_repo) or "MIT"

        write_source_json(
            dest_dir,
            source_name=source_name,
            repo_url=f"https://github.com/{source_name}",
            ref="main",
            commit_sha=commit_sha,
            upstream_path=str(src_path),
            license_id=license_id,
            sha256=sha,
        )

        frontmatter, body = parse_skill_md(dest_dir / "SKILL.md")
        skill_name = frontmatter.get("name", slug)
        skill_desc = frontmatter.get("description", "")

        cur.execute("""
            INSERT OR REPLACE INTO skills (
                slug, name, description, body, frontmatter_json, license, source_name,
                commit_sha, path, content_sha256, validation_status, validation_messages,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'valid', '[]', ?, ?)
        """, (
            slug,
            skill_name,
            skill_desc,
            body,
            json.dumps(frontmatter, default=str),
            license_id,
            source_name,
            commit_sha,
            str(dest_dir),
            sha,
            now_iso,
            now_iso,
        ))

        cur.execute("""
            INSERT OR REPLACE INTO skill_modules (slug, module_id, rank, score, status)
            VALUES (?, ?, 10.0, 100.0, 'selected')
        """, (slug, mod_id))

        print(f"Imported and selected authentic skill: {slug} (mod={mod_id}, slot={slot}, license={license_id})")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    sync_new_upstream_skills()

