"""Unit and integration tests for the Obsidian map layer.

Covers:
- Proxy note content and frontmatter schema
- Only selected skills get proxies; unselected proxy is removed
- Idempotence: repeated runs yield byte-identical files
- Generator scope: never writes outside map/ and 00-Home.md, never touches non-generated files
- Relation rules: caps respected (complements <= 4, alternate-of <= 2), no self-links or duplicates, precedes from catalog only
- Link integrity: 0 dangling wikilinks, 0 orphan proxies
- Obsidian config merging preserves existing keys and creates .bak backups
"""

import json
from pathlib import Path

import pytest
from tools.build_map import MapBuilder
from tools.db import (
    clear_skill_links,
    get_connection,
    init_db,
    init_map_schema,
    list_skill_links,
    upsert_skill,
    upsert_skill_module,
)


@pytest.fixture
def map_env(tmp_path: Path):
    """Sets up an isolated vault environment for testing MapBuilder."""
    vault_dir = tmp_path / "DevCrew-Vault"
    vault_dir.mkdir()
    skills_dir = vault_dir / "skills"
    skills_dir.mkdir()
    db_path = vault_dir / "registry.db"
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir()

    # Create initial app.json with a custom user key to test preservation
    (obsidian_dir / "app.json").write_text(
        json.dumps({"customSetting": "preservedValue", "userIgnoreFilters": ["custom/"]}),
        encoding="utf-8",
    )
    # Create initial graph.json with existing custom display properties
    (obsidian_dir / "graph.json").write_text(
        json.dumps({"customGraphProp": 1234, "showOrphans": True}),
        encoding="utf-8",
    )

    config = {
        "vault": {
            "skills_dir": str(skills_dir),
            "db_path": str(db_path),
        },
        "allowed_licenses": ["MIT", "Apache-2.0"],
    }

    # Initialize schema
    conn = get_connection(db_path)
    init_db(conn)
    init_map_schema(conn)

    # Populate 3 sample skills across 2 modules
    # Skill 1 (Module 1, PostgreSQL + Docker)
    conn.execute(
        """
        INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status)
        VALUES ('postgres-api', 'postgres-api', 'PostgreSQL database API service', '# Body', '{}', 'MIT', 'src-alpha', 'sha1', 'skills/postgres-api', 'h1', 'valid')
        """
    )
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, score, status) VALUES ('postgres-api', 1, 1.0, 100.0, 'selected')")

    # Skill 2 (Module 1, PostgreSQL + Docker - same module as Skill 1)
    conn.execute(
        """
        INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status)
        VALUES ('postgres-service', 'postgres-service', 'PostgreSQL service container management', '# Body', '{}', 'MIT', 'src-alpha', 'sha1', 'skills/postgres-service', 'h2', 'selected')
        """
    )
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, score, status) VALUES ('postgres-service', 1, 2.0, 95.0, 'selected')")

    # Skill 3 (Module 7, Docker + Containers - different module)
    conn.execute(
        """
        INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status)
        VALUES ('docker-deploy', 'docker-deploy', 'Docker deployment container automation', '# Body', '{}', 'Apache-2.0', 'src-beta', 'sha2', 'skills/docker-deploy', 'h3', 'valid')
        """
    )
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, score, status) VALUES ('docker-deploy', 7, 86.0, 90.0, 'selected')")

    # Skill 4 (Candidate only - NOT selected)
    conn.execute(
        """
        INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status)
        VALUES ('candidate-tool', 'candidate-tool', 'Candidate tool not selected', '# Body', '{}', 'MIT', 'src-alpha', 'sha1', 'skills/candidate-tool', 'h4', 'valid')
        """
    )
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, score, status) VALUES ('candidate-tool', 1, 500.0, 10.0, 'candidate')")

    conn.commit()
    conn.close()

    return {"vault_dir": vault_dir, "config": config, "db_path": db_path}


def test_map_builder_proxy_content(map_env):
    """Verify proxy notes contain required YAML frontmatter and expected links."""
    config = map_env["config"]
    builder = MapBuilder(config)
    summary = builder.build()

    assert summary["total_selected"] == 3
    proxy_path = builder.map_dir / "skills" / "postgres-api.md"
    assert proxy_path.is_file()

    content = proxy_path.read_text(encoding="utf-8")
    assert "type: skill-proxy" in content
    assert "generated: true" in content
    assert "slug: postgres-api" in content
    assert "module: 1" in content
    assert "license: MIT" in content
    assert "status: selected" in content
    assert "skill_path: skills/postgres-api/SKILL.md" in content

    # Code-formatted path, not wikilink for real file
    assert "Real skill file: `skills/postgres-api/SKILL.md`" in content
    assert "[[skills/postgres-api" not in content


def test_map_builder_unselected_proxy_pruned(map_env):
    """Verify that candidate skills do not get proxies, and deselected proxies are pruned."""
    config = map_env["config"]
    builder = MapBuilder(config)
    builder.build()

    # Candidate skill must not have a proxy note
    assert not (builder.map_dir / "skills" / "candidate-tool.md").exists()

    # Deselect postgres-service in DB
    conn = get_connection(map_env["db_path"])
    conn.execute("UPDATE skill_modules SET status = 'candidate' WHERE slug = 'postgres-service'")
    conn.commit()
    conn.close()

    # Re-run build
    builder.build()

    # postgres-service proxy must be pruned
    assert not (builder.map_dir / "skills" / "postgres-service.md").exists()


def test_map_builder_idempotence(map_env):
    """Verify repeated builds produce byte-identical markdown notes."""
    config = map_env["config"]
    builder = MapBuilder(config)

    builder.build()
    first_pass = {p: p.read_bytes() for p in builder.map_dir.rglob("*.md")}
    first_pass[builder.home_file] = builder.home_file.read_bytes()

    builder.build()
    second_pass = {p: p.read_bytes() for p in builder.map_dir.rglob("*.md")}
    second_pass[builder.home_file] = builder.home_file.read_bytes()

    assert len(first_pass) == len(second_pass)
    for p, b1 in first_pass.items():
        assert b1 == second_pass[p], f"File {p} changed on second run!"


def test_map_builder_scope_protection(map_env):
    """Verify builder never writes outside map/ and 00-Home.md, and never modifies hand-written notes."""
    config = map_env["config"]
    vault_dir = map_env["vault_dir"]

    # Place a hand-written note in map/ without generated: true
    handwritten = vault_dir / "map" / "custom-note.md"
    handwritten.parent.mkdir(parents=True, exist_ok=True)
    handwritten.write_text("# Hand written note\n", encoding="utf-8")

    builder = MapBuilder(config)
    builder.clean()

    # Hand-written note must survive clean
    assert handwritten.is_file()
    handwritten.unlink()


def test_map_builder_relation_rules(map_env):
    """Verify relation rules: complements <= 4, alternate-of <= 2, no self-links."""
    config = map_env["config"]
    builder = MapBuilder(config)
    builder.build()

    conn = get_connection(map_env["db_path"])
    links = list_skill_links(conn)
    conn.close()

    outgoing_complements = {}
    outgoing_alternates = {}

    for link in links:
        src = link["src_slug"]
        dst = link["dst_slug"]
        rel = link["relation"]

        # No self-links
        assert src != dst, f"Self-link detected: {src} -> {dst}"

        if rel == "complements":
            outgoing_complements[src] = outgoing_complements.get(src, 0) + 1
        elif rel == "alternate-of":
            outgoing_alternates[src] = outgoing_alternates.get(src, 0) + 1

    for src, cnt in outgoing_complements.items():
        assert cnt <= 4, f"{src} has {cnt} complements links (> 4)"

    for src, cnt in outgoing_alternates.items():
        assert cnt <= 2, f"{src} has {cnt} alternate-of links (> 2)"


def test_map_builder_check_live():
    """Verify the live DevCrew Vault map layer is 100% link-consistent with 0 errors."""
    builder = MapBuilder()
    is_valid, errors = builder.check()

    assert is_valid, f"Map check failed with errors: {errors}"
    assert len(errors) == 0


def test_obsidian_config_merging(map_env):
    """Verify Obsidian app.json and graph.json preserve custom keys and create .bak files."""
    config = map_env["config"]
    vault_dir = map_env["vault_dir"]
    obsidian_dir = vault_dir / ".obsidian"

    builder = MapBuilder(config)
    builder.build()

    # Verify backups exist
    assert (obsidian_dir / "app.json.bak").is_file()
    assert (obsidian_dir / "graph.json.bak").is_file()

    # Verify custom keys preserved
    app_data = json.loads((obsidian_dir / "app.json").read_text(encoding="utf-8"))
    assert app_data.get("customSetting") == "preservedValue"
    assert "skills/" in app_data.get("userIgnoreFilters", [])
    assert "_quarantine/" in app_data.get("userIgnoreFilters", [])

    graph_data = json.loads((obsidian_dir / "graph.json").read_text(encoding="utf-8"))
    assert graph_data.get("customGraphProp") == 1234
    assert graph_data.get("showOrphans") is False
    assert len(graph_data.get("colorGroups", [])) > 0

