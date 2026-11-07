"""
test_coverage.py — Tests for coverage-report generation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalog import generate_coverage_report, _build_default_catalog
from db import get_connection, init_db, upsert_skill, upsert_skill_module


def _make_skill(slug: str) -> dict:
    return {
        "slug": slug,
        "name": slug,
        "description": f"Use when you need {slug}.",
        "body": f"# {slug}\n\nContent.",
        "frontmatter_json": json.dumps({"name": slug}),
        "path": f"/tmp/{slug}",
        "content_sha256": "aabbcc",
        "validation_status": "valid",
        "source_name": "test",
        "license": "MIT",
        "has_scripts": 0,
        "has_references": 0,
        "has_assets": 0,
    }


@pytest.fixture()
def config_with_db(tmp_path):
    db_path = tmp_path / "registry.db"
    return {
        "_project_root": tmp_path,
        "vault": {"db_path": db_path},
    }


def test_coverage_report_created(config_with_db, tmp_path):
    db_path = Path(config_with_db["vault"]["db_path"])
    conn = get_connection(db_path)
    init_db(conn)

    # Insert a few skills and assign them to modules
    for slug, mid in [("api-design-principles", 1), ("react-best-practices", 2),
                      ("supabase", 3), ("semgrep", 4)]:
        upsert_skill(conn, _make_skill(slug))
        upsert_skill_module(conn, slug, mid, rank=1, score=10, status="selected")
    conn.close()

    report = generate_coverage_report(config_with_db)
    assert report.exists(), "coverage-report.md was not created"
    content = report.read_text(encoding="utf-8")
    assert "Coverage Report" in content
    assert "Module 1" in content


def test_coverage_report_shows_shortfall(config_with_db, tmp_path):
    db_path = Path(config_with_db["vault"]["db_path"])
    conn = get_connection(db_path)
    init_db(conn)
    # No skills → shortfall for every module
    conn.close()

    report = generate_coverage_report(config_with_db)
    content = report.read_text(encoding="utf-8")
    # Should show shortfall indicators
    assert "❌" in content


def test_coverage_report_no_shortfall_when_full(config_with_db, tmp_path):
    db_path = Path(config_with_db["vault"]["db_path"])
    conn = get_connection(db_path)
    init_db(conn)

    # Fill module 6 (target=10) exactly
    for i in range(10):
        slug = f"testing-skill-{i}"
        upsert_skill(conn, _make_skill(slug))
        upsert_skill_module(conn, slug, 6, rank=float(i), score=10, status="selected")
    conn.close()

    report = generate_coverage_report(config_with_db)
    content = report.read_text(encoding="utf-8")
    # Module 6 should show ✅
    lines = content.split("\n")
    module6_lines = [l for l in lines if "Testing, QA" in l]
    assert any("✅" in l for l in module6_lines), f"Expected ✅ for Module 6, got: {module6_lines}"

