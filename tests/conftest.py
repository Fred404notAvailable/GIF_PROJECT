"""
conftest.py — Shared fixtures for DevCrew Vault pytest suite.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

# Ensure tools/ is importable
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "tools"))


# ---------------------------------------------------------------------------
# Minimal valid config fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_project(tmp_path: Path) -> dict:
    """Create a minimal temporary project layout and return a config dict."""
    skills_dir = tmp_path / "skills"
    quarantine_dir = tmp_path / "_quarantine"
    staging_dir = tmp_path / ".staging"
    db_path = tmp_path / "registry.db"

    for d in (skills_dir, quarantine_dir, staging_dir):
        d.mkdir(parents=True)

    config = {
        "_project_root": tmp_path,
        "vault": {
            "skills_dir": skills_dir,
            "quarantine_dir": quarantine_dir,
            "staging_dir": staging_dir,
            "db_path": db_path,
        },
        "sources": [],
        "allowed_licenses": ["MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0"],
        "on_unknown_license": "quarantine",
        "on_slug_collision": "namespace",
        "validation": {
            "max_description_chars": 1024,
            "max_name_chars": 64,
            "warn_long_body_chars": 8000,
            "safety_patterns": ["curl\\s.*\\|\\s*sh", "rm\\s+-rf\\s+/"],
            "prompt_injection_patterns": ["ignore previous instructions"],
        },
        "watcher": {"debounce_ms": 500, "ignore_patterns": ["*.swp", ".DS_Store"]},
    }
    return config


@pytest.fixture()
def valid_skill(tmp_path: Path) -> Path:
    """Create a minimal valid skill folder and return its path."""
    skill_path = tmp_path / "my-skill"
    skill_path.mkdir()
    (skill_path / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Use when you need to test things.\n---\n# My Skill\n\nDoes something useful.\n",
        encoding="utf-8",
    )
    return skill_path


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Return an open in-memory SQLite connection with schema initialised."""
    from db import get_connection, init_db
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn

