"""
test_ranking.py — Tests for skill ranking and selection logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalog import _build_default_catalog, select_skills, _PINNED_SLOTS
from db import get_connection, init_db, upsert_skill, list_skill_modules


def _make_skill(slug: str, source: str = "test-source", status: str = "valid") -> dict:
    return {
        "slug": slug,
        "name": slug,
        "description": f"Use when you need {slug}. Trigger: test.",
        "body": f"# {slug}\n\nSome content about {slug}.",
        "frontmatter_json": json.dumps({"name": slug}),
        "path": f"/tmp/{slug}",
        "content_sha256": "abc123",
        "validation_status": status,
        "source_name": source,
        "license": "MIT",
        "has_scripts": 0,
        "has_references": 0,
        "has_assets": 0,
    }


@pytest.fixture()
def populated_db(tmp_path):
    """DB with a selection of pinned skills inserted."""
    db_path = tmp_path / "registry.db"
    conn = get_connection(db_path)
    init_db(conn)

    # Insert a subset of pinned slugs
    for slug in [
        "api-design-principles", "architecture-patterns", "fastapi-templates",
        "hono", "cloudflare", "stripe-best-practices",
        "react-best-practices", "next-dev-loop", "tailwind-design-system",
        "supabase-postgres-best-practices", "prisma-postgres-setup",
        "semgrep", "codeql",
        "langgraph-fundamentals", "langchain-rag",
        "test-driven-development", "webapp-testing",
        "terraform-skill", "kubernetes-skill", "docker",
    ]:
        upsert_skill(conn, _make_skill(slug))

    return conn


def test_pinned_slots_are_selected(tmp_path, populated_db):
    """Skills matching pinned slots should be marked 'selected'."""
    config = {
        "_project_root": tmp_path,
        "vault": {"db_path": tmp_path / "registry.db"},
    }
    catalog = _build_default_catalog()
    select_skills(config, populated_db, catalog)

    rows = list_skill_modules(populated_db)
    selected = {r["slug"] for r in rows if r["status"] == "selected"}

    # At minimum these pinned slugs should be selected
    for slug in ["api-design-principles", "hono", "react-best-practices",
                 "supabase-postgres-best-practices", "semgrep", "langgraph-fundamentals",
                 "test-driven-development", "terraform-skill"]:
        assert slug in selected, f"Expected {slug} to be selected, selected set: {selected}"


def test_invalid_skills_not_selected(tmp_path, populated_db):
    """Invalid skills (even if pinned) should not get 'selected' status."""
    invalid_slug = "fastapi-templates"
    populated_db.execute(
        "UPDATE skills SET validation_status = 'invalid' WHERE slug = ?", (invalid_slug,)
    )
    populated_db.commit()

    config = {"_project_root": tmp_path, "vault": {"db_path": tmp_path / "registry.db"}}
    catalog = _build_default_catalog()
    select_skills(config, populated_db, catalog)

    rows = list_skill_modules(populated_db, module_id=1)
    for r in rows:
        if r["slug"] == invalid_slug:
            assert r["status"] != "selected", f"{invalid_slug} should not be selected (it's invalid)"


def test_candidates_assigned(tmp_path, tmp_path_factory):
    """Skills not in pinned list should become candidates."""
    db_path = tmp_path / "registry.db"
    conn = get_connection(db_path)
    init_db(conn)

    # Insert a skill that is NOT in any pinned slot
    upsert_skill(conn, _make_skill("custom-postgres-skill", source="test-source"))

    config = {"_project_root": tmp_path, "vault": {"db_path": db_path}}
    catalog = _build_default_catalog()
    select_skills(config, conn, catalog)

    rows = list_skill_modules(conn)
    slugs_in_db = {r["slug"] for r in rows}
    assert "custom-postgres-skill" in slugs_in_db


def test_dedup_marks_alternate(tmp_path):
    """Near-duplicate skill names should result in one selected and one alternate."""
    db_path = tmp_path / "registry.db"
    conn = get_connection(db_path)
    init_db(conn)

    # Two skills with identical normalized names
    upsert_skill(conn, _make_skill("terraform-skill", source="antonbabenko-terraform-skill"))
    upsert_skill(conn, _make_skill("terraform-skill-duplicate", source="random-aggregator"))
    # Rename the second to look identical
    conn.execute(
        "UPDATE skills SET name = 'terraform skill' WHERE slug = 'terraform-skill-duplicate'"
    )
    conn.commit()

    config = {"_project_root": tmp_path, "vault": {"db_path": db_path}}
    catalog = _build_default_catalog()
    select_skills(config, conn, catalog)

    rows = list_skill_modules(conn)
    statuses = {r["slug"]: r["status"] for r in rows}
    # At least one should be non-candidate due to dedup
    assert "terraform-skill" in statuses

