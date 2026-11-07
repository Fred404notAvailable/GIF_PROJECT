"""
test_skill_modules_sync.py — Tests for skill_modules table sync after add/edit/delete.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalog import sync_skill_modules, _build_default_catalog
from db import get_connection, init_db, upsert_skill, list_skill_modules


def _make_skill(slug: str, source: str = "test", status: str = "valid") -> dict:
    return {
        "slug": slug,
        "name": slug,
        "description": f"Use when you need {slug}.",
        "body": f"# {slug}\nContent.",
        "frontmatter_json": json.dumps({"name": slug}),
        "path": f"/tmp/{slug}",
        "content_sha256": "deadbeef",
        "validation_status": status,
        "source_name": source,
        "license": "MIT",
        "has_scripts": 0,
        "has_references": 0,
        "has_assets": 0,
    }


@pytest.fixture()
def setup(tmp_path):
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    init_db(conn)
    catalog = _build_default_catalog()
    return conn, catalog


def test_add_pinned_skill_gets_selected(setup):
    conn, catalog = setup
    slug = "api-design-principles"  # pinned slot 1
    skill = _make_skill(slug)
    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)

    rows = list_skill_modules(conn)
    slugs = {r["slug"]: r["status"] for r in rows}
    assert slug in slugs
    assert slugs[slug] == "selected"


def test_add_unrecognized_skill_gets_candidate(setup):
    conn, catalog = setup
    slug = "my-custom-llm-thing"
    skill = _make_skill(slug)
    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)

    rows = list_skill_modules(conn)
    slugs = {r["slug"]: r["status"] for r in rows}
    assert slug in slugs
    assert slugs[slug] == "candidate"


def test_delete_removes_from_skill_modules(setup):
    conn, catalog = setup
    slug = "api-design-principles"
    skill = _make_skill(slug)
    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)

    # Verify it's there
    before = list_skill_modules(conn)
    assert any(r["slug"] == slug for r in before)

    # Now delete
    sync_skill_modules(slug, {}, conn, catalog, deleted=True)

    after = list_skill_modules(conn)
    assert not any(r["slug"] == slug for r in after)


def test_edit_updates_module_assignment(setup):
    conn, catalog = setup
    slug = "my-postgres-thing"
    skill = _make_skill(slug)
    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)

    # Update with richer database content
    updated = dict(skill)
    updated["description"] = "Use when managing PostgreSQL database schema migrations."
    updated["body"] = "PostgreSQL, database, schema, migration, Prisma."
    upsert_skill(conn, updated)
    sync_skill_modules(slug, updated, conn, catalog, deleted=False)

    rows = list_skill_modules(conn)
    matching = [r for r in rows if r["slug"] == slug]
    assert matching, f"{slug} should be in skill_modules"
    # Should now be classified in module 3 (Database)
    assert matching[0]["module_id"] == 3, (
        f"Expected module 3 after update, got {matching[0]['module_id']}"
    )


def test_rapid_add_delete_add(setup):
    """Rapid add → delete → add should end up with one candidate row."""
    conn, catalog = setup
    slug = "my-volatile-skill"
    skill = _make_skill(slug)

    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)
    sync_skill_modules(slug, {}, conn, catalog, deleted=True)
    upsert_skill(conn, skill)
    sync_skill_modules(slug, skill, conn, catalog, deleted=False)

    rows = list_skill_modules(conn)
    matches = [r for r in rows if r["slug"] == slug]
    assert len(matches) == 1

