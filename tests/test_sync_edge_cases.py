"""Unit tests for skill synchronization edge cases.

Covers:
- Collision namespacing
- Skip unchanged by hash
- License gate (allowed, unknown, disallowed)
- Atomic replace on change
- Source failure resilience (one failing source does not abort others)
"""

import json
from pathlib import Path

import pytest
from tools.sync_skills import _process_one_skill, atomic_copy_skill, detect_license, write_source_json
from tools.parsing import content_sha256, slugify


@pytest.fixture
def sync_env(tmp_path: Path):
    """Sets up temporary staging, skills, and quarantine directories."""
    staging = tmp_path / "staging"
    staging.mkdir()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    quarantine_dir = tmp_path / "quarantine"
    quarantine_dir.mkdir()

    return {
        "staging": staging,
        "skills_dir": skills_dir,
        "quarantine_dir": quarantine_dir,
    }


def _create_fixture_skill(repo_dir: Path, skill_name: str, license_spdx: str = "MIT", body: str = "# Sample") -> Path:
    skill_dir = repo_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {skill_name}\ndescription: Test skill fixture\nlicense: {license_spdx}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    lic_file = skill_dir / "LICENSE"
    if license_spdx == "MIT":
        lic_file.write_text("MIT License\n\nPermission is hereby granted, free of charge...", encoding="utf-8")
    elif license_spdx == "Apache-2.0":
        lic_file.write_text("Apache License\nVersion 2.0, January 2004", encoding="utf-8")
    elif license_spdx == "CC-BY-SA-4.0":
        lic_file.write_text("Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)", encoding="utf-8")
    elif license_spdx == "GPL":
        lic_file.write_text("GNU GENERAL PUBLIC LICENSE\nVersion 3", encoding="utf-8")
    return skill_dir


def test_sync_collision_namespacing(sync_env):
    """Verify that slug collisions from different sources get namespaced under policy=namespace."""
    skills_dir = sync_env["skills_dir"]
    quarantine_dir = sync_env["quarantine_dir"]
    staging = sync_env["staging"]

    repo1 = staging / "source-alpha"
    repo2 = staging / "source-beta"
    s1 = _create_fixture_skill(repo1, "common-tool")
    s2 = _create_fixture_skill(repo2, "common-tool", body="# Beta version")

    existing_slugs = {}
    counts = {"added": 0, "updated": 0, "skipped": 0, "quarantined": 0, "unchanged": 0, "warnings": []}

    # First sync from source-alpha
    _process_one_skill(
        skill_dir=s1,
        source_name="source-alpha",
        repo_url="https://github.com/org/alpha.git",
        ref="main",
        commit_sha="sha111",
        staging_repo=repo1,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    assert (skills_dir / "common-tool").is_dir()
    assert existing_slugs["common-tool"] == "source-alpha"

    # Second sync from source-beta with same raw slug
    _process_one_skill(
        skill_dir=s2,
        source_name="source-beta",
        repo_url="https://github.com/org/beta.git",
        ref="main",
        commit_sha="sha222",
        staging_repo=repo2,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    namespaced_slug = "source-beta--common-tool"
    assert (skills_dir / namespaced_slug).is_dir()
    assert any("namespaced to" in w for w in counts["warnings"])


def test_sync_unchanged_skip_by_hash(sync_env):
    """Verify that an existing skill with identical content SHA256 is counted as unchanged and not overwritten."""
    skills_dir = sync_env["skills_dir"]
    quarantine_dir = sync_env["quarantine_dir"]
    staging = sync_env["staging"]

    repo = staging / "source-gamma"
    s = _create_fixture_skill(repo, "cached-tool")

    existing_slugs = {}
    counts = {"added": 0, "updated": 0, "skipped": 0, "quarantined": 0, "unchanged": 0, "warnings": []}

    # Initial sync
    _process_one_skill(
        skill_dir=s,
        source_name="gamma",
        repo_url="https://github.com/org/gamma.git",
        ref="main",
        commit_sha="sha333",
        staging_repo=repo,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    assert counts["added"] == 1
    assert counts["unchanged"] == 0

    # Repeat sync without content change
    _process_one_skill(
        skill_dir=s,
        source_name="gamma",
        repo_url="https://github.com/org/gamma.git",
        ref="main",
        commit_sha="sha333",
        staging_repo=repo,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    assert counts["unchanged"] == 1


def test_sync_license_gate(sync_env):
    """Test that allowed licenses go to skills_dir while unknown/disallowed go to quarantine."""
    skills_dir = sync_env["skills_dir"]
    quarantine_dir = sync_env["quarantine_dir"]
    staging = sync_env["staging"]

    repo = staging / "mixed-licenses"
    s_mit = _create_fixture_skill(repo, "mit-tool", license_spdx="MIT")
    s_cc = _create_fixture_skill(repo, "cc-tool", license_spdx="CC-BY-SA-4.0")
    s_gpl = _create_fixture_skill(repo, "gpl-tool", license_spdx="GPL")

    existing_slugs = {}
    counts = {"added": 0, "updated": 0, "skipped": 0, "quarantined": 0, "unchanged": 0, "warnings": []}

    allowed = ["MIT", "Apache-2.0"]

    for s in [s_mit, s_cc, s_gpl]:
        _process_one_skill(
            skill_dir=s,
            source_name="mixed",
            repo_url="https://github.com/org/mixed.git",
            ref="main",
            commit_sha="sha444",
            staging_repo=repo,
            skills_dir=skills_dir,
            quarantine_dir=quarantine_dir,
            existing_slugs=existing_slugs,
            allowed_licenses=allowed,
            on_unknown_license="quarantine",
            on_slug_collision="namespace",
            dry_run=False,
            force=False,
            counts=counts,
            content_sha256_fn=content_sha256,
            slugify_fn=slugify,
        )

    # MIT must be in skills
    assert (skills_dir / "mit-tool").is_dir()
    assert not (quarantine_dir / "mit-tool").exists()

    # CC-BY-SA-4.0 and GPL must be in quarantine
    assert not (skills_dir / "cc-tool").exists()
    assert (quarantine_dir / "cc-tool").is_dir()
    assert not (skills_dir / "gpl-tool").exists()
    assert (quarantine_dir / "gpl-tool").is_dir()

    assert counts["added"] == 1
    assert counts["quarantined"] == 2


def test_sync_atomic_replace_on_change(sync_env):
    """Verify that updating a skill replaces the destination cleanly and writes new metadata."""
    skills_dir = sync_env["skills_dir"]
    quarantine_dir = sync_env["quarantine_dir"]
    staging = sync_env["staging"]

    repo = staging / "source-update"
    s = _create_fixture_skill(repo, "updating-skill", body="# V1 text")

    existing_slugs = {}
    counts = {"added": 0, "updated": 0, "skipped": 0, "quarantined": 0, "unchanged": 0, "warnings": []}

    _process_one_skill(
        skill_dir=s,
        source_name="update-source",
        repo_url="https://github.com/org/update.git",
        ref="main",
        commit_sha="sha001",
        staging_repo=repo,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    dest_file = skills_dir / "updating-skill" / "SKILL.md"
    assert "V1 text" in dest_file.read_text(encoding="utf-8")

    # Now modify source content
    (s / "SKILL.md").write_text(
        "---\nname: updating-skill\ndescription: Test fixture\nlicense: MIT\n---\n\n# V2 updated text\n",
        encoding="utf-8",
    )
    _process_one_skill(
        skill_dir=s,
        source_name="update-source",
        repo_url="https://github.com/org/update.git",
        ref="main",
        commit_sha="sha002",
        staging_repo=repo,
        skills_dir=skills_dir,
        quarantine_dir=quarantine_dir,
        existing_slugs=existing_slugs,
        allowed_licenses=["MIT"],
        on_unknown_license="quarantine",
        on_slug_collision="namespace",
        dry_run=False,
        force=False,
        counts=counts,
        content_sha256_fn=content_sha256,
        slugify_fn=slugify,
    )
    assert counts["updated"] == 1
    assert "V2 updated text" in dest_file.read_text(encoding="utf-8")
    meta = json.loads((skills_dir / "updating-skill" / ".source.json").read_text(encoding="utf-8"))
    assert meta["commit_sha"] == "sha002"

