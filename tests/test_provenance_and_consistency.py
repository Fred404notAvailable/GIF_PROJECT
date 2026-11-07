"""Unit and regression tests for provenance completeness and vault consistency.

Covers:
- Full verify_vault check on live database and skills directory
- .source.json provenance completeness
- Negative tests: detecting quarantined skills, invalid status, disallowed licenses
"""

import json
import sqlite3
from pathlib import Path

import pytest
from tools.config import load_config
from tools.verify_vault import verify_vault, VerificationReport
from tools.db import init_db


def test_vault_consistency_live():
    """Verify that the current DevCrew vault passes 100% of consistency checks."""
    config = load_config()
    report = verify_vault(config)

    assert report.passed, f"Vault consistency check failed with {len(report.failures)} failures: {report.failures}"
    assert report.total_selected == 100
    assert len(report.failures) == 0


def test_selected_skills_have_complete_source_json():
    """Verify every selected skill has a valid .source.json with all required provenance fields."""
    config = load_config()
    skills_dir = Path(config["vault"]["skills_dir"])
    db_path = Path(config["vault"]["db_path"])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT slug FROM skill_modules WHERE status = 'selected'")
    selected_slugs = [row["slug"] for row in c.fetchall()]
    conn.close()

    assert len(selected_slugs) == 100

    required_keys = {"repo_url", "commit_sha", "license", "content_sha256"}

    for slug in selected_slugs:
        source_json = skills_dir / slug / ".source.json"
        assert source_json.is_file(), f"Selected skill '{slug}' missing .source.json"

        data = json.loads(source_json.read_text(encoding="utf-8"))
        missing = required_keys - set(data.keys())
        assert not missing, f"Skill '{slug}' .source.json missing keys: {missing}"
        for k in required_keys:
            assert data[k], f"Skill '{slug}' .source.json has empty value for '{k}'"


def test_verify_vault_detects_quarantined_skill(tmp_path: Path):
    """Negative test: verify_vault flags a failure if a selected skill is in quarantine."""
    fake_skills = tmp_path / "skills"
    fake_skills.mkdir()
    fake_quar = tmp_path / "quarantine"
    fake_quar.mkdir()
    fake_db = tmp_path / "test.db"

    conn = sqlite3.connect(fake_db)
    init_db(conn)

    # Insert a skill that only exists in quarantine
    conn.execute("INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status) VALUES ('quarantined-tool', 'quarantined-tool', '', '', '{}', 'MIT', 'src', 'sha', '', 'hash', 'valid')")
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, status) VALUES ('quarantined-tool', 1, 1.0, 'selected')")
    conn.commit()
    conn.close()

    (fake_quar / "quarantined-tool").mkdir()

    cfg = {"allowed_licenses": ["MIT"]}
    report = verify_vault(config=cfg, db_path=fake_db, skills_dir=fake_skills, quarantine_dir=fake_quar)

    assert not report.passed
    assert len(report.failures) == 1
    assert "quarantine" in report.failures[0].errors[0]


def test_verify_vault_detects_disallowed_license(tmp_path: Path):
    """Negative test: verify_vault flags a failure if a selected skill has a license outside allowed_licenses."""
    fake_skills = tmp_path / "skills"
    fake_skills.mkdir()
    fake_quar = tmp_path / "quarantine"
    fake_quar.mkdir()
    fake_db = tmp_path / "test.db"

    conn = sqlite3.connect(fake_db)
    init_db(conn)

    conn.execute("INSERT INTO skills (slug, name, description, body, frontmatter_json, license, source_name, commit_sha, path, content_sha256, validation_status) VALUES ('gpl-tool', 'gpl-tool', '', '', '{}', 'GPL-3.0', 'src', 'sha', '', 'hash', 'valid')")
    conn.execute("INSERT INTO skill_modules (slug, module_id, rank, status) VALUES ('gpl-tool', 1, 1.0, 'selected')")
    conn.commit()
    conn.close()

    skill_folder = fake_skills / "gpl-tool"
    skill_folder.mkdir()
    (skill_folder / ".source.json").write_text(
        json.dumps({"repo_url": "http://x", "commit_sha": "c1", "license": "GPL-3.0", "content_sha256": "h1"}),
        encoding="utf-8",
    )

    cfg = {"allowed_licenses": ["MIT", "Apache-2.0"]}
    report = verify_vault(config=cfg, db_path=fake_db, skills_dir=fake_skills, quarantine_dir=fake_quar)

    assert not report.passed
    assert len(report.failures) == 1
    assert any("not in allowed_licenses" in err for err in report.failures[0].errors)
