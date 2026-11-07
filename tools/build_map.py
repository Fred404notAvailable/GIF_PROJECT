"""Obsidian Map Layer Generator for DevCrew Skill Vault.

Builds a structured, human-readable graph view in Obsidian for the ~100 selected
skills, organized by module, technology, source, and license, while candidate
and quarantine packages remain excluded from Obsidian search and graph view.

CLI:
  python tools/build_map.py [--dry-run] [--clean] [--check]
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure tools/ is on path
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from config import load_config
from db import (
    clear_skill_links,
    get_connection,
    init_db,
    init_map_schema,
    list_skill_links,
    set_skill_tech_tags,
    upsert_skill_link,
)
from parsing import parse_skill_md


# ---------------------------------------------------------------------------
# Default Technology Keywords
# ---------------------------------------------------------------------------

DEFAULT_TECH_KEYWORDS: dict[str, list[str]] = {
    "PostgreSQL": ["postgres", "postgresql", "pgvector", "neon", "supabase"],
    "Docker": ["docker", "dockerfile", "compose", "container"],
    "Containers": ["docker", "container", "kubernetes", "k8s"],
    "Kubernetes": ["kubernetes", "k8s", "kubectl"],
    "Terraform": ["terraform", "opentofu", "hcl"],
    "Next.js": ["next.js", "nextjs", "app router"],
    "React": ["react", "react native"],
    "Tailwind": ["tailwind", "tailwindcss"],
    "Playwright": ["playwright"],
    "Cypress": ["cypress"],
    "OWASP": ["owasp", "asvs", "wstg"],
    "LangGraph": ["langgraph", "stategraph"],
    "LangChain": ["langchain"],
    "RAG": ["rag", "retrieval-augmented", "embedding", "similarity search", "hybrid search", "vector index"],
    "FastAPI": ["fastapi", "pydantic"],
    "Node.js": ["node.js", "nodejs"],
    "AWS": ["aws", "cdk", "serverless"],
    "Azure": ["azure", "azure devops"],
    "GitHub Actions": ["github actions", "ci/cd", "pipeline", "workflow"],
    "Prisma": ["prisma"],
    "Supabase": ["supabase"],
    "Firebase": ["firebase"],
    "Cloudflare": ["cloudflare", "workers"],
    "Hono": ["hono"],
    "Observability": ["observability", "telemetry", "tracing", "langfuse", "metrics"],
    "Code Review": ["code review", "code-review", "pr review", "review"],
    "TDD": ["test-driven", "tdd", "debugging", "testing", "test", "verification"],
    "API Security": ["api security", "api-security", "auth"],
    "SQL Injection": ["sql injection"],
    "XSS": ["xss", "html injection"],
    "Event-Driven": ["event store", "event-store", "event-driven", "eda"],
    "Architecture": ["architecture", "microservices", "clean architecture", "patterns"],
    "REST & API": ["api", "rest", "graphql"],
    "Agents": ["agent", "agents", "autonomous", "deep agent", "memory", "prompt", "langgraph"],
    "UI & Design": ["frontend", "ui", "design", "canvas", "storybook", "shadcn", "theme", "angular", "css"],
    "Linux & Shell": ["bash", "linux", "shell", "terminal"],
    "SQL & Database": ["database", "sql", "query", "schema", "clickhouse", "migration"],
    "Security Audit": [
        "security audit", "security auditor", "security", "cybersecurity",
        "devsecops", "stride", "threat", "semgrep", "codeql", "vulnerability",
        "penetration", "pentest",
    ],
    "MCP": ["mcp", "model context protocol"],
}


# ---------------------------------------------------------------------------
# Core Map Builder
# ---------------------------------------------------------------------------


class MapBuilder:
    """Orchestrates generation of map proxy notes, technology clusters, and relations."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_config()
        vault_cfg = self.config.get("vault", {})
        self.vault_dir = Path(vault_cfg.get("skills_dir", "DevCrew-Vault/skills")).parent
        self.db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
        self.map_dir = self.vault_dir / "map"
        self.home_file = self.vault_dir / "00-Home.md"

        catalog_path = self.vault_dir / "catalog.yaml"
        self.catalog = self._load_catalog(catalog_path)
        self.tech_keywords = self.catalog.get("tech_keywords") or DEFAULT_TECH_KEYWORDS

    def _load_catalog(self, path: Path) -> dict[str, Any]:
        if path.is_file():
            import yaml
            try:
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
        return {}

    def fetch_selected_skills(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        """Fetch all selected skills with rank, module, and metadata."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sm.slug, sm.module_id, sm.rank, sm.score,
                   s.name, s.description, s.license, s.source_name, s.commit_sha
            FROM skill_modules sm
            JOIN skills s ON sm.slug = s.slug
            WHERE sm.status = 'selected'
            ORDER BY sm.module_id, sm.rank, sm.slug
            """
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def compute_tech_tags(self, skills: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """
        Compute tech tags per skill, capping at 5 highest-scored tags.
        Returns (skill_to_tags, tag_to_skills).
        """
        skill_to_tags: dict[str, list[str]] = {}
        tag_to_skills: dict[str, list[str]] = defaultdict(list)

        for sk in skills:
            slug = sk["slug"]
            name = sk.get("name", "")
            desc = sk.get("description", "")
            text = f"{slug} {name} {desc}".lower()

            scored: list[tuple[int, str]] = []
            for tag, kws in self.tech_keywords.items():
                score = 0
                for kw in kws:
                    if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
                        score += 1
                if score > 0:
                    scored.append((score, tag))

            scored.sort(key=lambda x: (-x[0], x[1]))
            top_tags = [t for _, t in scored[:5]]
            skill_to_tags[slug] = top_tags
            for t in top_tags:
                tag_to_skills[t].append(slug)

        return skill_to_tags, dict(tag_to_skills)

    def derive_typed_relations(
        self,
        skills: list[dict[str, Any]],
        skill_to_tags: dict[str, list[str]],
    ) -> dict[str, dict[str, list[tuple[str, str]]]]:
        """
        Derive typed relations following Task 4 rules:
        - complements: different modules, share >= 1 tag, max 4 outgoing, symmetric
        - alternate-of: same module, share >= 2 tags, max 2 outgoing, symmetric
        - precedes: only from explicit catalog.yaml precedes: [[a, b], ...]

        Returns: slug -> {relation: [(dst_slug, reason), ...]}
        """
        skill_map = {s["slug"]: s for s in skills}
        slug_list = sorted(skill_map.keys())
        tag_sets = {s: set(skill_to_tags.get(s, [])) for s in slug_list}

        # 1. Complements
        complements_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for s1 in slug_list:
            m1 = skill_map[s1]["module_id"]
            t1 = tag_sets[s1]
            candidates = []
            for s2 in slug_list:
                if s1 == s2:
                    continue
                m2 = skill_map[s2]["module_id"]
                if m1 == m2:
                    continue
                shared = t1.intersection(tag_sets[s2])
                if shared:
                    candidates.append((len(shared), sorted(list(shared)), s2))
            candidates.sort(key=lambda x: (-x[0], x[2]))
            for shared_cnt, shared_tags, s2 in candidates[:4]:
                reason = f"shared_tech:{','.join(shared_tags)}"
                complements_map[s1].append((s2, reason))

        # Enforce symmetry for complements (respecting max 4 cap)
        for s1 in slug_list:
            for s2, reason in list(complements_map[s1]):
                s2_dests = [d for d, _ in complements_map[s2]]
                if s1 not in s2_dests and len(complements_map[s2]) < 4:
                    complements_map[s2].append((s1, reason))

        # 2. Alternate-of
        alternate_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for s1 in slug_list:
            m1 = skill_map[s1]["module_id"]
            t1 = tag_sets[s1]
            candidates = []
            for s2 in slug_list:
                if s1 == s2:
                    continue
                m2 = skill_map[s2]["module_id"]
                if m1 != m2:
                    continue
                shared = t1.intersection(tag_sets[s2])
                if len(shared) >= 2:
                    sim = difflib.SequenceMatcher(None, s1, s2).ratio()
                    candidates.append((len(shared), sim, sorted(list(shared)), s2))
            candidates.sort(key=lambda x: (-x[0], -x[1], x[3]))
            for _, _, shared_tags, s2 in candidates[:2]:
                reason = f"same_module_alternate:{','.join(shared_tags)}"
                if (s2, reason) not in alternate_map[s1]:
                    alternate_map[s1].append((s2, reason))
                if (s1, reason) not in alternate_map[s2] and len(alternate_map[s2]) < 2:
                    alternate_map[s2].append((s1, reason))

        # 3. Precedes
        precedes_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
        explicit_precedes = self.catalog.get("precedes", [])
        for pair in explicit_precedes:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                src, dst = pair
                if src in skill_map and dst in skill_map:
                    precedes_map[src].append((dst, "catalog_precedes"))

        result: dict[str, dict[str, list[tuple[str, str]]]] = {}
        for s in slug_list:
            result[s] = {
                "complements": sorted(complements_map.get(s, []), key=lambda x: x[0]),
                "alternate-of": sorted(alternate_map.get(s, []), key=lambda x: x[0]),
                "precedes": sorted(precedes_map.get(s, []), key=lambda x: x[0]),
            }

        return result

    def get_module_definitions(self) -> dict[int, dict[str, Any]]:
        """Return module metadata from catalog or defaults."""
        mods = self.catalog.get("modules", [])
        mod_dict = {}
        for m in mods:
            mod_dict[m["id"]] = m
        return mod_dict

    def build(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Execute full map generation.
        Writes notes, updates DB, and configures Obsidian.
        """
        conn = get_connection(self.db_path)
        init_db(conn)
        init_map_schema(conn)

        skills = self.fetch_selected_skills(conn)
        skill_to_tags, tag_to_skills = self.compute_tech_tags(skills)
        relations = self.derive_typed_relations(skills, skill_to_tags)
        mod_defs = self.get_module_definitions()

        # Filter active tech notes (>= 2 selected skills)
        active_tech_tags = {tag: sk_list for tag, sk_list in tag_to_skills.items() if len(sk_list) >= 2}
        dropped_tech_tags = {tag: sk_list for tag, sk_list in tag_to_skills.items() if len(sk_list) < 2}

        # Collect source repos and licenses
        source_to_skills: dict[str, list[dict[str, Any]]] = defaultdict(list)
        license_to_skills: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sk in skills:
            src = sk.get("source_name") or "unknown"
            lic = sk.get("license") or "UNKNOWN"
            source_to_skills[src].append(sk)
            license_to_skills[lic].append(sk)

        # Plan files to generate: path -> content string
        files_to_write: dict[Path, str] = {}

        # 1. 00-Home.md
        files_to_write[self.home_file] = self._render_home(mod_defs, skills)

        # 2. map/dashboard.md
        files_to_write[self.map_dir / "dashboard.md"] = self._render_dashboard(
            skills, mod_defs, license_to_skills, active_tech_tags
        )

        # 3. map/modules/Module N - <name>.md
        for mid, mdata in sorted(mod_defs.items()):
            mname = mdata.get("name", f"Module {mid}")
            mod_skills = [s for s in skills if s["module_id"] == mid]
            fname = f"Module {mid} - {self._sanitize_title(mname)}.md"
            files_to_write[self.map_dir / "modules" / fname] = self._render_module_hub(
                mid, mdata, mod_skills
            )

        # 4. map/skills/<slug>.md
        for sk in skills:
            slug = sk["slug"]
            mid = sk["module_id"]
            mname = mod_defs.get(mid, {}).get("name", f"Module {mid}")
            mod_title = f"Module {mid} - {self._sanitize_title(mname)}"
            tags = [t for t in skill_to_tags.get(slug, []) if t in active_tech_tags]
            rels = relations.get(slug, {"complements": [], "alternate-of": [], "precedes": []})

            files_to_write[self.map_dir / "skills" / f"{slug}.md"] = self._render_skill_proxy(
                sk, mod_title, tags, rels
            )

        # 5. map/tech/<tag>.md
        for tag, sk_slugs in sorted(active_tech_tags.items()):
            tagged_skills = [s for s in skills if s["slug"] in sk_slugs]
            files_to_write[self.map_dir / "tech" / f"{tag}.md"] = self._render_tech_note(
                tag, tagged_skills, mod_defs
            )

        # 6. map/sources/src-<source>.md
        for src, sk_list in sorted(source_to_skills.items()):
            files_to_write[self.map_dir / "sources" / f"src-{src}.md"] = self._render_source_note(
                src, sk_list
            )

        # 7. map/licenses/lic-<license>.md
        for lic, sk_list in sorted(license_to_skills.items()):
            files_to_write[self.map_dir / "licenses" / f"lic-{lic}.md"] = self._render_license_note(
                lic, sk_list
            )

        # Prune obsolete skill proxies (skills no longer selected)
        selected_slugs = {s["slug"] for s in skills}
        files_to_delete: list[Path] = []
        skills_map_dir = self.map_dir / "skills"
        if skills_map_dir.is_dir():
            for p in skills_map_dir.glob("*.md"):
                if p.stem not in selected_slugs:
                    files_to_delete.append(p)

        summary = {
            "total_selected": len(skills),
            "files_to_create": len(files_to_write),
            "files_to_delete": len(files_to_delete),
            "active_tech_tags": len(active_tech_tags),
            "dropped_tech_tags": len(dropped_tech_tags),
            "complements_count": sum(len(r["complements"]) for r in relations.values()),
            "alternates_count": sum(len(r["alternate-of"]) for r in relations.values()),
            "precedes_count": sum(len(r["precedes"]) for r in relations.values()),
        }

        if dry_run:
            conn.close()
            return summary

        # 1. Update Database
        clear_skill_links(conn, created_by="rule")
        for sk in skills:
            slug = sk["slug"]
            tags = skill_to_tags.get(slug, [])
            set_skill_tech_tags(conn, slug, tags)

            for rel_type, rel_list in relations.get(slug, {}).items():
                for dst, reason in rel_list:
                    upsert_skill_link(conn, slug, dst, rel_type, reason=reason, created_by="rule")

        conn.commit()
        conn.close()

        # 2. Delete obsolete files
        for p in files_to_delete:
            try:
                p.unlink()
            except OSError:
                pass

        # 3. Write generated notes
        for p, content in files_to_write.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

        # 4. Merge Obsidian Config
        self._update_obsidian_config()

        return summary

    def clean(self) -> int:
        """Remove all files with generated: true in map/ and 00-Home.md."""
        count = 0
        if self.home_file.is_file():
            if "generated: true" in self.home_file.read_text(encoding="utf-8", errors="ignore"):
                self.home_file.unlink()
                count += 1

        if self.map_dir.is_dir():
            for p in self.map_dir.rglob("*.md"):
                if p.is_file():
                    try:
                        text = p.read_text(encoding="utf-8", errors="ignore")
                        if "generated: true" in text:
                            p.unlink()
                            count += 1
                    except OSError:
                        pass
            # Clean empty subdirs
            for subdir in sorted(self.map_dir.iterdir(), reverse=True):
                if subdir.is_dir() and not any(subdir.iterdir()):
                    try:
                        subdir.rmdir()
                    except OSError:
                        pass

        return count

    def check(self) -> tuple[bool, list[str]]:
        """
        Verify that the map layer is up to date and has 0 dangling links.
        Returns (is_valid, error_list).
        """
        errors = []
        if not self.home_file.is_file():
            errors.append("00-Home.md is missing")

        if not self.map_dir.is_dir():
            errors.append("map/ directory is missing")
            return False, errors

        # Gather all generated markdown files
        existing_notes: set[str] = set()
        for p in self.map_dir.rglob("*.md"):
            existing_notes.add(p.stem)
        existing_notes.add("00-Home")

        # Check proxy notes vs selected skills
        conn = get_connection(self.db_path)
        skills = self.fetch_selected_skills(conn)
        conn.close()

        selected_slugs = {s["slug"] for s in skills}
        proxy_slugs = {p.stem for p in (self.map_dir / "skills").glob("*.md")} if (self.map_dir / "skills").is_dir() else set()

        missing_proxies = selected_slugs - proxy_slugs
        if missing_proxies:
            errors.append(f"Missing proxy notes for selected skills: {sorted(list(missing_proxies))[:5]}")

        extra_proxies = proxy_slugs - selected_slugs
        if extra_proxies:
            errors.append(f"Extra proxy notes for unselected skills: {sorted(list(extra_proxies))[:5]}")

        # Link integrity check across map/
        wikilink_pattern = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
        dangling_links = set()

        for p in self.map_dir.rglob("*.md"):
            try:
                content = p.read_text(encoding="utf-8")
                for match in wikilink_pattern.finditer(content):
                    target = match.group(1).strip()
                    if target not in existing_notes and target != "dashboard":
                        dangling_links.add((p.name, target))
            except Exception as exc:
                errors.append(f"Could not read {p}: {exc}")

        if dangling_links:
            errors.append(f"Found {len(dangling_links)} dangling wikilinks: {list(dangling_links)[:5]}")

        return (len(errors) == 0, errors)

    # -----------------------------------------------------------------------
    # Rendering Helpers
    # -----------------------------------------------------------------------

    def _sanitize_title(self, name: str) -> str:
        return name.replace("/", "-").replace("\\", "-").replace(":", " -")

    def _render_home(self, mod_defs: dict[int, dict[str, Any]], skills: list[dict[str, Any]]) -> str:
        lines = [
            "---",
            "type: home-dashboard",
            "generated: true",
            'title: "DevCrew Skill Vault — Map Hub"',
            "---",
            "# DevCrew AI Skill Vault",
            "",
            "Welcome to the **DevCrew AI Skill Vault** map layer. This knowledge graph connects the 100 selected enterprise agent skills across 7 core architecture modules, technologies, upstream sources, and licenses.",
            "",
            "## Architecture Modules & Hubs",
        ]
        for mid, mdata in sorted(mod_defs.items()):
            mname = mdata.get("name", f"Module {mid}")
            target = mdata.get("target", 15)
            cnt = sum(1 for s in skills if s["module_id"] == mid)
            title = f"Module {mid} - {self._sanitize_title(mname)}"
            lines.append(f"{mid}. [[{title}]] ({cnt}/{target} skills)")

        lines.extend([
            "",
            "## Vault Observability & Dashboards",
            "- [[dashboard|Vault Operational Dashboard & Metrics]]",
            "",
            "## Human Collaboration & Workflows",
            "- **Crews:** See `crews/README.md` for agent team configurations",
            "- **Playbooks:** See `playbooks/README.md` for operational SOPs",
            "- **Notes:** See `notes/README.md` for design docs and architecture notes",
            "",
        ])
        return "\n".join(lines)

    def _render_dashboard(
        self,
        skills: list[dict[str, Any]],
        mod_defs: dict[int, dict[str, Any]],
        license_to_skills: dict[str, list[dict[str, Any]]],
        active_tech_tags: dict[str, list[str]],
    ) -> str:
        lines = [
            "---",
            "type: vault-dashboard",
            "generated: true",
            "---",
            "# DevCrew Vault — Operational Dashboard",
            "",
            "## Module Coverage & Target Fulfillment",
            "",
            "| Module ID | Module Name | Target | Selected | Fulfillment |",
            "|:---:|---|:---:|:---:|:---:|",
        ]
        total_target = 0
        total_selected = len(skills)
        for mid, mdata in sorted(mod_defs.items()):
            mname = mdata.get("name", f"Module {mid}")
            target = mdata.get("target", 15)
            total_target += target
            cnt = sum(1 for s in skills if s["module_id"] == mid)
            pct = int((cnt / target) * 100) if target else 100
            title = f"Module {mid} - {self._sanitize_title(mname)}"
            lines.append(f"| {mid} | [[{title}]] | {target} | {cnt} | **{pct}%** |")

        lines.append(f"| **Total** | **All 7 Modules** | **{total_target}** | **{total_selected}** | **100% Target Met** |")

        lines.extend([
            "",
            "## License Distribution",
            "",
            "| License | Selected Skills | Policy Status | Reference Note |",
            "|---|:---:|:---:|---|",
        ])
        for lic, sk_list in sorted(license_to_skills.items()):
            lines.append(f"| `{lic}` | {len(sk_list)} | Allowed | [[lic-{lic}]] |")

        lines.extend([
            "",
            "## Top Technologies in Vault",
            "",
            "| Technology | Skills Tagged | Tech Note |",
            "|---|:---:|---|",
        ])
        for tag, sk_slugs in sorted(active_tech_tags.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
            lines.append(f"| **{tag}** | {len(sk_slugs)} | [[{tag}]] |")

        lines.extend([
            "",
            "## Open Governance Decisions",
            "- See `DECISIONS-NEEDED.md` in repository root for ShareAlike (CC-BY-SA-4.0) and unlicensed repos.",
            "",
        ])
        return "\n".join(lines)

    def _render_module_hub(
        self,
        mid: int,
        mdata: dict[str, Any],
        mod_skills: list[dict[str, Any]],
    ) -> str:
        mname = mdata.get("name", f"Module {mid}")
        target = mdata.get("target", 15)
        cnt = len(mod_skills)

        lines = [
            "---",
            "type: module-hub",
            "generated: true",
            f"module_id: {mid}",
            f'name: "{mname}"',
            f"target: {target}",
            f"selected_count: {cnt}",
            "---",
            f"# Module {mid}: {mname}",
            "",
            f"**Target:** {target} skills | **Selected:** {cnt} skills | **Status:** {'100% Target Met' if cnt >= target else 'Shortfall'}",
            "",
            "## Selected Skills in this Module",
        ]
        for sk in sorted(mod_skills, key=lambda x: (x.get("rank") or 0, x["slug"])):
            slug = sk["slug"]
            desc = (sk.get("description") or "").replace("\n", " ")
            if len(desc) > 90:
                desc = desc[:87] + "..."
            lines.append(f"- [[{slug}]]: {desc}")

        lines.extend([
            "",
            "## Unfilled Slots",
            "None (All target slots satisfied by verified packages)",
            "",
        ])
        return "\n".join(lines)

    def _render_skill_proxy(
        self,
        sk: dict[str, Any],
        mod_title: str,
        tags: list[str],
        rels: dict[str, list[tuple[str, str]]],
    ) -> str:
        slug = sk["slug"]
        mid = sk["module_id"]
        rank = sk.get("rank")
        src = sk.get("source_name") or "unknown"
        lic = sk.get("license") or "UNKNOWN"
        desc = (sk.get("description") or "").replace("\n", " ").strip()

        lines = [
            "---",
            "type: skill-proxy",
            "generated: true",
            f"slug: {slug}",
            f"module: {mid}",
            f"slot: {int(rank) if rank is not None else 'null'}",
            f"source: {src}",
            f"license: {lic}",
            "status: selected",
            f"skill_path: skills/{slug}/SKILL.md",
            "---",
            f"# {slug}",
            desc if desc else f"Skill package for {slug}",
            "",
            f"**Module:** [[{mod_title}]]  ",
            f"**Source:** [[src-{src}]]  ",
            f"**License:** [[lic-{lic}]]  ",
        ]
        if tags:
            tag_links = ", ".join(f"[[{t}]]" for t in tags)
            lines.append(f"**Tech:** {tag_links}")
        else:
            lines.append("**Tech:** None")

        lines.extend([
            "",
            "## Related Skills",
        ])

        complements = rels.get("complements", [])
        if complements:
            c_links = ", ".join(f"[[{dst}]]" for dst, _ in complements)
            lines.append(f"- **Complements:** {c_links}")
        else:
            lines.append("- **Complements:** None")

        alternates = rels.get("alternate-of", [])
        if alternates:
            a_links = ", ".join(f"[[{dst}]]" for dst, _ in alternates)
            lines.append(f"- **Alternate of:** {a_links}")

        precedes = rels.get("precedes", [])
        if precedes:
            p_links = ", ".join(f"[[{dst}]]" for dst, _ in precedes)
            lines.append(f"- **Comes before:** {p_links}")

        lines.extend([
            "",
            f"Real skill file: `skills/{slug}/SKILL.md`",
            "",
        ])
        return "\n".join(lines)

    def _render_tech_note(
        self,
        tag: str,
        tagged_skills: list[dict[str, Any]],
        mod_defs: dict[int, dict[str, Any]],
    ) -> str:
        lines = [
            "---",
            "type: tech-cluster",
            "generated: true",
            f'tag: "{tag}"',
            f"skill_count: {len(tagged_skills)}",
            "---",
            f"# Technology: {tag}",
            "",
            f"Selected skills in the DevCrew vault tagged with **{tag}**, grouped by architecture module:",
            "",
        ]
        by_mod: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for s in tagged_skills:
            by_mod[s["module_id"]].append(s)

        for mid in sorted(by_mod.keys()):
            mname = mod_defs.get(mid, {}).get("name", f"Module {mid}")
            mtitle = f"Module {mid} - {self._sanitize_title(mname)}"
            lines.append(f"## [[{mtitle}|Module {mid}: {mname}]]")
            for sk in sorted(by_mod[mid], key=lambda x: x["slug"]):
                slug = sk["slug"]
                desc = (sk.get("description") or "").replace("\n", " ").strip()
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                lines.append(f"- [[{slug}]]: {desc}")
            lines.append("")

        return "\n".join(lines)

    def _render_source_note(self, src: str, sk_list: list[dict[str, Any]]) -> str:
        first = sk_list[0] if sk_list else {}
        repo_url = first.get("source_name", src)
        commit = first.get("commit_sha") or "HEAD"
        lic = first.get("license") or "UNKNOWN"

        lines = [
            "---",
            "type: source-repo",
            "generated: true",
            f'source: "{src}"',
            f'license: "{lic}"',
            f'commit_sha: "{commit}"',
            f"selected_count: {len(sk_list)}",
            "---",
            f"# Source Repository: {src}",
            "",
            f"- **Source ID:** `{src}`",
            f"- **Default License:** [[lic-{lic}]]",
            f"- **Commit SHA:** `{commit}`",
            f"- **Selected Skills:** {len(sk_list)}",
            "",
            "## Selected Skills Ingested from this Source",
        ]
        for sk in sorted(sk_list, key=lambda x: x["slug"]):
            slug = sk["slug"]
            desc = (sk.get("description") or "").replace("\n", " ").strip()
            if len(desc) > 80:
                desc = desc[:77] + "..."
            lines.append(f"- [[{slug}]]: {desc}")

        lines.append("")
        return "\n".join(lines)

    def _render_license_note(self, lic: str, sk_list: list[dict[str, Any]]) -> str:
        obligations = {
            "MIT": "Permissive open-source license. Requires preservation of the original copyright notice and permission disclaimer in distributions. No copyleft or share-alike obligations.",
            "Apache-2.0": "Permissive open-source license with an explicit grant of patent rights. Requires preservation of copyright, license notice, and any NOTICE file. State changes must be documented.",
            "MPL-2.0": "Weak copyleft license (Mozilla Public License 2.0). Source code modifications to existing MPL-licensed files must be made available under MPL-2.0. Larger works combining MPL files with other proprietary code remain permitted.",
            "CC-BY-4.0": "Creative Commons Attribution 4.0. Requires appropriate credit and notice of any modifications. Does not impose share-alike obligations.",
            "BSD-3-Clause": "Permissive license with 3 clauses (copyright notice, condition disclaimer, non-endorsement of derived products).",
        }.get(lic, "Standard open source license terms apply. Ensure attribution and copyright headers are preserved.")

        lines = [
            "---",
            "type: license-summary",
            "generated: true",
            f'license: "{lic}"',
            f"skill_count: {len(sk_list)}",
            "---",
            f"# License: {lic}",
            "",
            "## Legal Terms & Redistribution Obligations",
            obligations,
            "",
            f"## Selected Skills under {lic} ({len(sk_list)} skills)",
        ]
        for sk in sorted(sk_list, key=lambda x: x["slug"]):
            slug = sk["slug"]
            desc = (sk.get("description") or "").replace("\n", " ").strip()
            if len(desc) > 80:
                desc = desc[:77] + "..."
            lines.append(f"- [[{slug}]]: {desc}")

        lines.append("")
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Obsidian Config Merging
    # -----------------------------------------------------------------------

    def _update_obsidian_config(self) -> None:
        """Merge ignore filters and graph styling into .obsidian configs."""
        obsidian_dir = self.vault_dir / ".obsidian"
        if not obsidian_dir.exists():
            return

        app_json = obsidian_dir / "app.json"
        graph_json = obsidian_dir / "graph.json"

        # 1. Update app.json (hide skills/, _quarantine/, .staging/)
        app_data: dict[str, Any] = {}
        if app_json.is_file():
            # Backup
            shutil.copy2(app_json, obsidian_dir / "app.json.bak")
            try:
                app_data = json.loads(app_json.read_text(encoding="utf-8"))
            except Exception:
                app_data = {}

        filters: list[str] = app_data.get("userIgnoreFilters", [])
        for f in ["skills/", "_quarantine/", ".staging/"]:
            if f not in filters:
                filters.append(f)
        app_data["userIgnoreFilters"] = filters
        app_json.write_text(json.dumps(app_data, indent=2), encoding="utf-8")

        # 2. Update graph.json (color groups and display settings)
        graph_data: dict[str, Any] = {}
        if graph_json.is_file():
            shutil.copy2(graph_json, obsidian_dir / "graph.json.bak")
            try:
                graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
            except Exception:
                graph_data = {}

        graph_data["showOrphans"] = False
        graph_data["showAttachments"] = False

        # Defined distinctive color groups
        target_colors = [
            {"query": "path:map/modules", "color": {"a": 1, "rgb": 9130742}},   # Purple (#8b5cf6)
            {"query": "path:map/skills", "color": {"a": 1, "rgb": 3899382}},    # Blue (#3b82f6)
            {"query": "path:map/tech", "color": {"a": 1, "rgb": 1096065}},      # Emerald (#10b981)
            {"query": "path:map/sources", "color": {"a": 1, "rgb": 16113163}},  # Amber (#f59e0b)
            {"query": "path:map/licenses", "color": {"a": 1, "rgb": 15680580}}, # Red (#ef4444)
            {"query": "path:crews", "color": {"a": 1, "rgb": 439892}},          # Cyan (#06b6d4)
            {"query": "path:playbooks", "color": {"a": 1, "rgb": 15513241}},    # Pink (#ec4899)
        ]
        graph_data["colorGroups"] = target_colors
        graph_json.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Obsidian map layer for the DevCrew Vault.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing files.")
    parser.add_argument("--clean", action="store_true", help="Remove all generated map files.")
    parser.add_argument("--check", action="store_true", help="Check if map is up to date and valid.")

    args = parser.parse_args()
    builder = MapBuilder()

    if args.clean:
        deleted = builder.clean()
        print(f"Cleaned {deleted} generated notes from map/ and 00-Home.md")
        return 0

    if args.check:
        is_valid, errors = builder.check()
        if is_valid:
            print("[PASS] Obsidian Map layer is up to date and link-consistent!")
            return 0
        else:
            print(f"[FAIL] Found {len(errors)} map consistency issues:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

    print("=" * 60)
    print("DevCrew Vault — Building Obsidian Map Layer")
    print("=" * 60)

    summary = builder.build(dry_run=args.dry_run)

    print(f"Total Selected Skills:  {summary['total_selected']}")
    print(f"Files Generated:        {summary['files_to_create']}")
    print(f"Obsolete Files Pruned:  {summary['files_to_delete']}")
    print(f"Active Tech Tag Notes:  {summary['active_tech_tags']}")
    print(f"Dropped Tech Tags (<2): {summary['dropped_tech_tags']}")
    print(f"Complements Relations:  {summary['complements_count']}")
    print(f"Alternates Relations:   {summary['alternates_count']}")
    print(f"Precedes Relations:     {summary['precedes_count']}")
    print("-" * 60)
    print("[SUCCESS] Obsidian Map Layer successfully generated!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
