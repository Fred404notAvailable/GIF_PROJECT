"""Vault consistency checker.

Verifies that:
1. Every selected skill exists under DevCrew-Vault/skills/ (and NOT _quarantine/).
2. Every selected skill has validation_status in ('valid', 'valid-with-warnings').
3. Every selected skill has a license in allowed_licenses.
4. Every selected skill has a complete .source.json (repo_url, commit_sha, license, content_sha256).

Can be executed as a standalone CLI script or imported into pytest test suites.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import load_config
from sync_skills import detect_license


@dataclass
class VerificationFailure:
    module_id: int
    slug: str
    errors: list[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    total_selected: int = 0
    failures: list[VerificationFailure] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0


def verify_vault(
    config: dict[str, Any] | None = None,
    db_path: Path | None = None,
    skills_dir: Path | None = None,
    quarantine_dir: Path | None = None,
) -> VerificationReport:
    """Run all consistency checks on the current vault state."""
    if config is None:
        config = load_config()

    allowed_licenses = set(config.get("allowed_licenses", []))
    if not allowed_licenses:
        raise ValueError("Configuration missing 'allowed_licenses' list")

    vault_cfg = config.get("vault", {})
    if db_path is None:
        db_path = Path(vault_cfg.get("db_path", "DevCrew-Vault/registry.db"))
    if skills_dir is None:
        skills_dir = Path(vault_cfg.get("skills_dir", "DevCrew-Vault/skills"))
    if quarantine_dir is None:
        quarantine_dir = Path(vault_cfg.get("quarantine_dir", "DevCrew-Vault/_quarantine"))

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found at '{db_path}'")

    report = VerificationReport()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute("""
            SELECT sm.module_id, sm.slug, s.license, s.validation_status, s.source_name, s.path
            FROM skill_modules sm
            LEFT JOIN skills s ON sm.slug = s.slug
            WHERE sm.status = 'selected'
            ORDER BY sm.module_id, sm.rank
        """)
        rows = c.fetchall()
        report.total_selected = len(rows)

        for row in rows:
            mod_id = row["module_id"]
            slug = row["slug"]
            db_lic = row["license"] or ""
            v_status = row["validation_status"] or "unknown"

            errors = []
            skill_folder = skills_dir / slug
            quar_folder = quarantine_dir / slug

            # Check 1: Must exist in skills_dir and not in quarantine
            if not skill_folder.is_dir():
                if quar_folder.is_dir():
                    errors.append(f"Skill '{slug}' is present in quarantine, not skills dir")
                else:
                    errors.append(f"Skill '{slug}' directory missing from disk")
            elif quar_folder.is_dir():
                errors.append(f"Skill '{slug}' is duplicated in both skills and _quarantine")

            # Check 2: Validation status
            if v_status not in ("valid", "valid-with-warnings"):
                errors.append(f"Validation status is '{v_status}' (must be valid or valid-with-warnings)")

            # Check 3: License check
            folder_lic = detect_license(skill_folder, skill_folder) if skill_folder.is_dir() else "UNKNOWN"
            resolved_lic = folder_lic if folder_lic != "UNKNOWN" else db_lic
            if resolved_lic not in allowed_licenses:
                errors.append(
                    f"License '{resolved_lic}' is not in allowed_licenses ({allowed_licenses})"
                )

            # Check 4: .source.json check
            source_json = skill_folder / ".source.json"
            if not source_json.is_file():
                errors.append("Missing .source.json provenance file")
            else:
                try:
                    s_data = json.loads(source_json.read_text(encoding="utf-8"))
                    required_keys = ["repo_url", "commit_sha", "license", "content_sha256"]
                    missing_keys = [k for k in required_keys if not s_data.get(k)]
                    if missing_keys:
                        errors.append(f".source.json missing required keys: {missing_keys}")
                except Exception as exc:
                    errors.append(f".source.json is corrupted or invalid JSON: {exc}")

            if errors:
                report.failures.append(VerificationFailure(module_id=mod_id, slug=slug, errors=errors))

    finally:
        conn.close()

    return report


def main() -> int:
    """CLI entry point for python tools/verify_vault.py."""
    print("=" * 60)
    print("DevCrew Skill Vault Consistency Check")
    print("=" * 60)

    try:
        report = verify_vault()
    except Exception as exc:
        print(f"[FAIL] Could not run consistency verification: {exc}", file=sys.stderr)
        return 1

    print(f"Total Selected Skills: {report.total_selected}")
    if report.passed:
        print("[PASS] All selected skills meet 100% of consistency and license rules!")
        return 0

    print(f"[FAIL] Found {len(report.failures)} failing selected skills:")
    for failure in report.failures:
        print(f"  - Module {failure.module_id} | {failure.slug}:")
        for err in failure.errors:
            print(f"      * {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

