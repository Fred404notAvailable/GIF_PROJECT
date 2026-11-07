"""Unit tests for the watcher lifecycle and event filtering.

Covers:
- create, edit, delete indexing
- debounce behavior (collapsing rapid calls)
- invalid edit followed by fix
- ignored temp files (.tmp, .swp, ~)
- ignored .obsidian/ directory changes
"""

import time
from pathlib import Path

import pytest
from tools.watcher import Debouncer, Indexer, _should_ignore
from tools.db import get_connection, init_db, list_skills, get_skill


@pytest.fixture
def test_vault(tmp_path: Path):
    """Sets up a test vault folder and isolated SQLite db."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    db_path = tmp_path / "test_vault.db"

    config = {
        "vault": {
            "skills_dir": str(skills_dir),
            "db_path": str(db_path),
        },
        "allowed_licenses": ["MIT", "Apache-2.0"],
    }
    return {"skills_dir": skills_dir, "db_path": db_path, "config": config}


def _make_skill(skills_dir: Path, slug: str, desc: str = "Use when running test workflows in test fixtures", lic: str = "MIT", body: str = "# Body\n") -> Path:
    s_dir = skills_dir / slug
    s_dir.mkdir(parents=True, exist_ok=True)
    (s_dir / "SKILL.md").write_text(
        f"---\nname: {slug}\ndescription: {desc}\nlicense: {lic}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return s_dir


def test_watcher_create_edit_delete(test_vault):
    """Verify Indexer handles creation, modification, and deletion cleanly."""
    cfg = test_vault["config"]
    skills_dir = test_vault["skills_dir"]
    indexer = Indexer(cfg)

    # 1. Create
    s_dir = _make_skill(skills_dir, "my-tool", desc="Use when version 1 is requested")
    indexer.index_skill("my-tool", s_dir)

    sk = get_skill(indexer._conn, "my-tool")
    assert sk is not None
    assert sk["slug"] == "my-tool"
    assert "version 1" in sk["description"]
    assert sk["validation_status"] in ("valid", "valid-with-warnings")

    # 2. Edit
    _make_skill(skills_dir, "my-tool", desc="Use when version 2 is requested")
    indexer.index_skill("my-tool", s_dir, force=True)
    sk2 = get_skill(indexer._conn, "my-tool")
    assert "version 2" in sk2["description"]

    # 3. Delete
    indexer.remove_skill("my-tool")
    sk3 = get_skill(indexer._conn, "my-tool")
    assert sk3 is None

    indexer.close()


def test_watcher_debouncer():
    """Verify Debouncer collapses multiple rapid triggers into one callback."""
    calls = []

    def callback(slug, val):
        calls.append((slug, val))

    debouncer = Debouncer(delay_ms=50, callback=callback)

    # Trigger 5 rapid events for the same slug
    for i in range(5):
        debouncer.trigger("rapid-slug", i)

    # Wait for debounce to fire
    time.sleep(0.12)
    assert len(calls) == 1
    assert calls[0] == ("rapid-slug", 4)

    debouncer.flush()


def test_watcher_invalid_then_fix(test_vault):
    """Verify that an invalid edit marks status='invalid', and subsequent fix restores 'valid'."""
    cfg = test_vault["config"]
    skills_dir = test_vault["skills_dir"]
    indexer = Indexer(cfg)

    # Create valid
    s_dir = _make_skill(skills_dir, "fixable-skill", desc="Use when validating and fixing skills")
    indexer.index_skill("fixable-skill", s_dir)
    assert get_skill(indexer._conn, "fixable-skill")["validation_status"] in ("valid", "valid-with-warnings")

    # Make invalid (corrupt frontmatter yaml)
    (s_dir / "SKILL.md").write_text("NOT_FRONTMATTER\nNo yaml here\n", encoding="utf-8")
    indexer.index_skill("fixable-skill", s_dir, force=True)
    assert get_skill(indexer._conn, "fixable-skill")["validation_status"] == "invalid"

    # Fix it
    _make_skill(skills_dir, "fixable-skill", desc="Use when fixing and restoring skills")
    indexer.index_skill("fixable-skill", s_dir, force=True)
    assert get_skill(indexer._conn, "fixable-skill")["validation_status"] in ("valid", "valid-with-warnings")

    indexer.close()


def test_watcher_ignored_temp_files():
    """Verify temp files, lock files, and swap files are flagged as ignored."""
    patterns = [".swp", "~", ".DS_Store", ".tmp", "__pycache__"]
    ignored_samples = [
        Path("skills/my-tool/.test.tmp"),
        Path("skills/my-tool/SKILL.md~"),
        Path("skills/my-tool/.SKILL.md.swp"),
        Path("skills/my-tool/tmp.part"),
    ]
    for p in ignored_samples[:3]:
        assert _should_ignore(p, patterns), f"Expected {p} to be ignored"

    # Real file must NOT be ignored
    assert not _should_ignore(Path("skills/my-tool/SKILL.md"), patterns)
    assert not _should_ignore(Path("skills/my-tool/scripts/run.py"), patterns)


def test_watcher_ignored_obsidian_dir():
    """Verify changes inside .obsidian/ directory are completely ignored."""
    patterns = [".swp", "~", ".DS_Store", ".tmp", "__pycache__"]
    obsidian_paths = [
        Path("skills/.obsidian/workspace.json"),
        Path("skills/.obsidian/app.json"),
        Path("skills/.obsidian/plugins/core/data.json"),
    ]
    for p in obsidian_paths:
        assert _should_ignore(p, patterns), f"Expected {p} in .obsidian to be ignored"
